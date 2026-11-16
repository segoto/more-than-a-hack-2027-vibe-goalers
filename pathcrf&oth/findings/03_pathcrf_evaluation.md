# 03 — PathCRF evaluation

**PathCRF: Ball-Free Soccer Event Detection via Possession Path Inference from Player
Trajectories** — Hyunsung Kim et al., KDD 2026.
[paper](https://arxiv.org/abs/2602.12080) · [code](https://github.com/hyunsungkim-ds/pathcrf)
(read from a local clone; not vendored into this repo).

## Relation to `docs/PATHCRF_ANALYSIS.md`

The team already has an analysis of the same library (in Spanish). The two agree on the facts
(inputs, CRF rules, gap-free 11 v 11 requirement, alive-only episodes, Sportec as the key external
dataset). They differ on one judgement call:

- `PATHCRF_ANALYSIS.md`: don't run the model; take its **ideas** (constrained Viterbi, minimum
  duration, Sportec for tuning) into a light numpy pipeline.
- This document: same critical path, plus running the **pretrained weights unchanged** as an extra
  evidence stream *if* someone has time to build the 22 continuous lanes. Running pretrained
  external weights locally as an input is allowed; fine-tuning on this match is not.

Both agree the light pipeline must ship on its own.

## Verdict up front

**Applicable, and the most relevant thing we have found** — it answers "who has the ball at each
moment" from players alone, which is exactly what we lack on 41% of frames. But it is **not a
drop-in**: it expects clean, gap-free, 11-vs-11 trajectories inside known ball-alive episodes,
and was trained on a different league and tracking provider. Its value for us is as **one evidence
stream** fused with the tracked ball and Smart Tagging, not as the labeller.

## 1. What it does

At every time step it selects **exactly one edge** of a dynamic graph over the 22 players plus 4
"outside" nodes (`out_left`, `out_right`, `out_bottom`, `out_top` — the four pitch boundaries):

| edge | meaning |
|---|---|
| `A → A` (self-loop) | player A is in possession |
| `A → B` | the ball is travelling from A to B (pass / clearance / shot…) |
| `A → out_x` | the ball is travelling out of the pitch over that line |
| `out_x → out_x` | the ball is out (stays until the episode ends) |

Event detection = a change of edge. Team possession = the team of the edge's *source* node (or,
during a pass, split by sender/receiver team).

## 2. How it works

**Input per node, per frame** (`dataset.py`, `node_in_dim = 8`):
`[team indicator (−1 left / +1 right), goalkeeper flag, x, y, vx, vy, speed, accel]`
in metres on a 105 × 68 pitch. **No ball features** in the released models (`ball_feature=False`).
Teams are reordered left-team-first; the GK is detected as the player whose mean x is furthest
from halfway.

**Temporal sampling:** 25 fps → **5 fps** (every 5th frame); **10 s windows**; at inference,
windows overlap by 50% and are blended with linear ramps.

**Backbone:** Set-Attention (Set Transformer) over players per time step → per-node and per-edge
embeddings → temporal Set Attention / LSTM → edge logits (26 × 26 candidate edges).

**CRF:** a structured layer that makes the edge sequence *physically consistent*. Allowed
transitions (`models/dynamic_sparse_crf.py::_build_allowed_next`):

- from `A→A` (A holds): next edge must start at A → `A→A`, `A→teammate`, `A→opponent`, `A→out`
- from `A→B` (in flight): stay `A→B`, or B starts → `B→B`, `B→teammate`, `B→opponent`, `B→out`
- from `A→out`: stay, or `out→out`
- `out→out` is absorbing

So the ball can't teleport: possession only moves along an edge the ball actually travels.
"Dynamic" CRF = transition scores are computed from the current edge embeddings (context-dependent),
"sparse/masked" = forbidden transitions are masked out. Decoding is Viterbi.

**Training data:** the open **Sportec / DFL dataset** (7 Bundesliga 1 & 2 matches, TRACAB-style
optical tracking + manually annotated events, events synced to tracking with ELASTIC). Labels =
per-frame possessing player from synced events. Leave-one-match-out CV.

**Released weights** (`saved/`, ~19 MB each): non-CRF (100), static dense (110), static masked
(120), dynamic dense (130), **dynamic masked (140, the paper's main model)**.

**Reported validation** (`saved/140/log.txt`, held-out match, per 0.2 s step):

| | |
|---|---|
| edge accuracy | ~0.71 |
| source-node accuracy | ~0.80 |
| destination-node accuracy | ~0.85 |

That is *player-level* accuracy over 26 nodes. Team-level possession — what we need — must be
substantially higher, but the logs don't report it; we'd have to measure it (see 05).

## 3. Fit to our problem

### What matches well

| | |
|---|---|
| **Ball-free** | works on exactly the frames where our ball is missing |
| **Anonymous players are fine** | permutation-equivariant set attention — slot identity is never used, only team + GK flag |
| **Physically consistent sequences** | the CRF removes the flicker that destroys spellF1 |
| **Out-of-play edges** | `A→out_x` gives a direct "ball went out" signal for the D start edge, and says which line (throw-in vs goal kick/corner) |
| **Event times** | the paper is about precise event detection — boundary precision is what spellF1 rewards |
| **Pretrained weights + MPL-2.0 licence** | inspectable and usable; MPL is file-level copyleft (modified PathCRF files stay MPL; our own files are unaffected) |
| **5 fps** | a 0.2 s step is ≤ 5 frames — fine for spellF1's tolerance |

### Gaps and risks

| gap | severity | why |
|---|---|---|
| **Needs gap-free 11 v 11 trajectories** | **high** | inference returns `None` for an episode if *any* input feature is NaN (`inference_episode`). Our ATD: 46 slots, ~20.5 objects per graded frame, gaps, duplicates. We must build 22 continuous "lanes" ourselves. |
| **Needs ball-alive episodes as input** | **high** | it models possession *within* live play; it does not detect stoppages (`episode_id` comes from `ball_state == alive` in the training data). Our D detector must segment episodes first. A→out edges help, fouls/offsides don't show. |
| **Touch ≠ control** | medium | it detects *every* on-ball action. A deflection appears as a short opponent self-loop. The repo's `_overwrite_short_self_loops(min_dur)` merges short holds; we additionally need our control rule (02). |
| **Domain shift** | medium | Bundesliga, TRACAB-quality tracking, 7 matches → LaLiga, Metrica automatic tracking with noise and jitter. Velocities/accelerations from noisy positions will be noisier → smooth before differentiating. |
| **Velocity/accel features** | medium | must be computed by us; ATD gives speed only; derive vx, vy, accel from smoothed positions at 25 fps, then subsample. |
| **Pitch orientation & units** | low | ATD is 0–1 normalised, origin convention to verify; multiply by 105.3 × 68.0 (games.py) and match PathCRF's origin-at-corner 0–105 / 0–68 frame. Teams switch sides at half time; the model reorders left-first per phase, so we must supply the per-half orientation. |
| **Dependencies** | low/med | needs `torch` + `torch_geometric` (not in its `requirements.txt`); this machine is Python 3.14 with an App-Control block on pandas DLLs. CPU inference on ~106 min × 5 fps ≈ 32k steps is cheap. |
| **Not trained on this match** | n/a — good | no rule issue: pretrained on other games' human labels is explicitly allowed. Must be documented in the tech doc. |

### Is "joining it to the tracked ball" sensible? Yes — they are complementary

| | tracked ball | PathCRF |
|---|---|---|
| available | 59% of graded frames | ~100% of live frames (once lanes are built) |
| precise when available | yes — metres | weaker (~0.8 source accuracy, player level) |
| fails | crowded boxes, duels, aerial balls | ambiguous duels, long balls, noisy tracks |
| knows dead ball | partly (out of bounds, still ball) | only "ball went out" |

The ball is **high precision, low coverage**; PathCRF is **high coverage, lower precision**. They
fail in partly different places. Fuse them as evidence in one decoder (see 05) rather than
overwriting one with the other.

## 4. How to apply it — concrete pipeline

1. **Episodes:** run our D detector → ball-alive intervals per half.
2. **Lanes (the critical engineering step):** per episode, per team, assign ATD track slots to
   11 lanes so each lane is spatially continuous:
   - link tracklets end→start by Hungarian assignment on a physically reachable cost
     (distance ÷ gap time ≤ ~10 m/s), within a team;
   - interpolate short gaps (linear / constant velocity), drop duplicates (two slots < ~0.5 m apart),
     fill long gaps by holding position (a formation prior would have to come from external
     data, not be estimated on this match);
   - GK lane = the player deepest toward own goal, frame by frame. Note: PathCRF's own
     `detect_keepers` / `label_phases` average positions over a whole period of *this* match —
     our `docs/PATHCRF_ANALYSIS.md` flags that as a grey zone (**NO GO** until confirmed), so use
     a per-frame or documented rule instead.
   - Every threshold here (reachable speed, duplicate distance, max interpolated gap) must be a
     physical prior or come from external data, documented next to the parameter.

   **Identity doesn't need to be true, only spatially continuous**: if two lanes swap people
   while they're next to each other, the inputs barely change. This is the one place where the
   identity-switch problem matters to us.
3. **Features:** smooth positions (e.g. Savitzky–Golay), derive vx, vy, speed, accel, convert to
   metres and PathCRF's frame, subsample to 5 fps.
4. **Inference:** model 140, 10 s windows, 50% overlap. Keep the **soft edge probabilities**, not
   only the Viterbi path.
5. **Collapse to teams:** P(H in control at t) = Σ P(self-loops of H players) + a share of
   in-flight edges (sender team early in the flight, receiver team late — or leave in-flight mass
   as "keep previous team"). P(out) from edges into outside nodes.
6. **Upsample** to 25 fps and feed into the fused decoder (05).

**Effort estimate:** lanes + features ≈ the bulk (a day for a robust version); environment +
inference ≈ hours; fusion ≈ hours. With a 2026-11-17 deadline this is **a stretch goal running in
parallel**, not the critical path. The classical pipeline (ball + kinematics + tags + HSMM) must
ship on its own.

## 5. Open questions to check locally when data lands

- What fraction of live time has ≥ 10 players per team visible? (decides how much lane-filling is
  invented vs observed)
- ATD origin/orientation, and whether `speed` is reliable enough to skip differentiation.
- How often PathCRF and the visible ball agree on this match. **Allowed only as an automatic
  sanity check** (the clarification allows "automatic checks using only the provided data").
  **Using that agreement to set fusion weights or thresholds would be calibrating on the provided
  game → not allowed.** The weights must come from the external dev set (05); this number can only
  raise a flag ("something is broken"), never pick a parameter.
