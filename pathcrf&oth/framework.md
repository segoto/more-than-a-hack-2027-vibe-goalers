# Possession decision framework

How we decide `H` / `A` / `D` for every frame. PathCRF, the tracked ball and the other signals are
combined into one decision process designed to **reproduce how the ground truth was produced**.
Data quality (cleaning, track lanes, ball recovery) is layer 0 and is covered only as an input
contract here.

Status: design proposal, to be agreed before implementation.

---

## 1. Target: what process generated the ground truth?

We cannot see how the labels were made, but the organisers' text and the public window constrain
it tightly.

| evidence | source | inference |
|---|---|---|
| "derived from corrected tracking … `D` where it marks the ball dead, otherwise the team it names as owning it. Nothing smoothed" | `CHALLENGE.md` | two per-frame fields from a corrected (human-reviewed) tracking product: **ball state** and **ball owner** |
| "the tracking names a team even while the ball is out of play — whoever will restart, or touched it last" | `CHALLENGE.md` | the owner field is a **persistent possession state**, carried through stoppages. It is not a per-frame nearest-player measure |
| loose/contested ball stays with the last team; deflections, touches without control and aerial duels without subsequent control do not switch | `CHALLENGE.md` | owner switches only on a **gain-of-control event** by the opponent |
| spells of 0.76 s and 1.32 s in the public window | public GT, read for semantics only | the control requirement is **short**: a brief controlled touch can switch ownership |
| the state opens on the kickoff team at the first graded frame; `D` ends exactly at the restart | public GT | `D` = [stoppage, restart touch); the restart team owns the ball from the restart frame |
| vocabulary: *interception*, *deflection*, *aerial duel won/lost*, *controlled* | `CHALLENGE.md` | matches **Metrica's event taxonomy** (`BALL OUT`, `SET PIECE`, `RECOVERY`, `BALL LOST`, `CHALLENGE` in Metrica's open sample data) |
| DFL's open data defines possession as "the player in control of the ball" and ball status as "inactive when the match is interrupted by the referee" | IDSSE dataset paper | an independent provider with the same two-field design, so the per-frame state-machine reading of H0 is the industry convention |

**Working hypothesis (H0):** the ground truth is an **event-driven possession state machine**:

```
owner(t)  = team of the last player who gained control before t
            (switches at the gain-of-control frame; never smoothed)
state(t)  = DEAD from the stoppage frame (ball out / whistle) to the restart frame, else ALIVE
label(t)  = D if DEAD else owner(t)
```

Our system mimics this process. We **detect gain-of-control events and stoppages** and run the same
state machine on them. We do not classify frames independently. Everything below serves that.

H0 is a hypothesis. We refine it only from documentation, from the label semantics visible in the
public window (no numbers taken), and from Metrica's own open data, if its licence allows.

---

## 2. Architecture

```
L0  DATA QUALITY (input contract)
    ATD players → cleaned, smoothed, 22 continuous lanes (team, GK flag, x, y, vx, vy, speed, accel)
    ATD ball    → cleaned + short-gap interpolation + optional video re-detection (FootAndBall)
    homography, Smart Tagging → frame-aligned
        │
L1  EVIDENCE (independent sensors, each with its own confidence)
    E1 ball–player touch sensor        E2 PathCRF possession-path posteriors
    E3 team-shape / pressing sensor    E4 dead-ball sensors      E5 Smart Tagging priors
        │
L2  EVENTS  — candidate gain-of-control events (time, team, player, confidence, kind)
              candidate stoppage/restart events (time, kind, restart team)
        │
L3  DECODER — team-level semi-Markov state machine (Viterbi per half)
              states: H-ctrl, H-flight, A-ctrl, A-flight, DEAD
        │
L4  OUTPUT  — {H-ctrl, H-flight}→H, {A-ctrl, A-flight}→A, DEAD→D; no X inside play
```

Why this shape:

- The decoder is offline, so every boundary lands on the event frame that started it. This is how
  the ground truth behaves: a switch at the gain of control, without lag.
- The sensors fail in different places, so each one only contributes evidence. None of them
  decides on its own.
- PathCRF appears twice: as a sensor (E2) and as the **template for the decoder** (L3), whose
  transition rules are a team-level copy of PathCRF's CRF.

---

## 3. L1 — Evidence sensors

### E1. Ball–player touch sensor (when the ball is observed)

- **Touch candidates.** A touch is a kink in the ball trajectory: a direction change ≥ θ, from
  Ramer–Douglas–Peucker simplification, as in PathCRF's preprocessing, or a speed jump. It is
  assigned to the nearest player within r_touch.
- **Control.** After the touch, the ball stays within r_ctrl of the same player for ≥ d_dwell, or
  the next touch is a teammate's (a completed pass).
- **Duel flag.** Two opponents are both within r_duel of the ball. Evidence here is down-weighted
  and deferred to E2 and to what happens next.
- **Output:** per-frame P_ball(team in control), plus discrete touch events with a confidence.

### E2. PathCRF (on every live frame)

- Run the released dynamic-masked model unchanged on the 22 lanes, in 10 s windows with 50 %
  overlap at 5 fps.
- Keep the **soft edge posteriors** and collapse them to the team level:
  - P_path(H-ctrl) = Σ P(self-loops of H players)
  - P_path(H-flight) = Σ P(H player → any node)
  - and the same for A
  - P_path(out) = Σ P(edges into or between the outside nodes)
- **Events:** changes in the Viterbi edge sequence: control onsets, pass starts, ball out.

What E2 adds even when the ball is visible: it models **who is moving with the ball and who is
receiving**. That is exactly what nearest-player logic gets wrong in duels, on deflections and on
first-time passes. It also gives an independent check on E1's touch events.

### E3. Team shape and pressing (weak, always available)

- Features: team centroid velocities along the attacking axis, team length and width, how many
  players converge on one opponent (pressing), and the defensive line's depth.
- Output: a weak P_shape(team in possession). Its job is to break ties in long ball gaps and to
  confirm turnovers within about 2 s.

### E4. Dead-ball sensors

| signal | marks |
|---|---|
| ball outside the pitch lines (ATD or video detection), or last seen at a line and then lost | stoppage start, and which line |
| PathCRF mass into an outside node | stoppage start, and which line |
| collective deceleration (mean speed collapse, no sprints) | stoppage start (fouls, offside) |
| ball stationary ≥ d_still at a restart location | restart pending |
| set-piece formations: corner cluster, wall, kickoff halves, GK in the 6-yard box, a player on the touchline | restart type |
| collective acceleration, plus the ball leaving its still position | restart frame |
| Smart Tagging `SET PIECES` (with `Type`), `GOALS` | restart type and approximate time |
| optional: referee whistle in the audio | stoppage start |

### E5. Smart Tagging priors

- `BUILD UP`, `PROGRESSION`, `CREATING CHANCES` and `ATTACKING TRANSITION` name the **team in
  possession**.
- `DEFENDING IN …` and `DEFENSIVE TRANSITION` name the team **without** it, so they are inverted.
- Tags mark phases, not possession edges. They are used as a weak, slow prior; they never place a
  boundary.

---

## 4. L2 — Events

The ground truth is driven by events, so we build an explicit event list before decoding.

**Gain-of-control event** for team T at time t, requiring:
- a touch by a T player (E1), or a PathCRF control onset by a T player (E2), or both within a
  tolerance τ (agreement raises the confidence); and
- **confirmation** within the following window: a dwell ≥ d_dwell, or a completed T pass, or a
  T-favouring shift in E3.

These do **not** produce gain-of-control events, following the challenge's rules:
- a single touch followed by the previous owner touching again (a deflection or tackle without
  control);
- a duel touch with no subsequent T control;
- an aerial contact (high ball speed, no dwell) with no subsequent T control.

**Stoppage event:** from E4, with a kind (out over a touchline or goal line, whistle, goal, end of
half).

**Restart event:** from E4, with a kind and a restart team, assigned by the laws of the game:

| stoppage | restart team |
|---|---|
| ball out over a touchline or goal line | **the opposite of the last touch's team** (throw-in, goal kick or corner) |
| goal | the conceding team (kickoff) |
| foul or offside | the fouled team: the team of the player nearest the ball when it starts moving, cross-checked with the formation |
| start of half | the kickoff team: the team with players at the centre spot |

Each event carries a confidence, which becomes a log-score in the decoder.

---

## 5. L3 — Decoder

A team-level copy of PathCRF's CRF, with football laws added:

```
            pass completed (same team)
        ┌───────────────────────────────┐
        ▼                               │
   H-ctrl ──── pass start ────► H-flight ┘
     │  ▲                          │
     │  │ gain of control by H     │ gain of control by A (interception)
     │  └──────── A-flight ◄───────┼──────────── A-ctrl ...  (symmetric)
     │                             ▼
     └──── stoppage ────► DEAD ◄── stoppage (ball out from flight)
                           │
                           └── restart ──► {H|A}-ctrl  (restart team from L2)
```

- **Allowed transitions:**
  - ctrl → flight (same team)
  - flight → ctrl (same team: pass; other team: turnover)
  - ctrl → ctrl of the other team, only via a gain-of-control event (tackle won)
  - any live state → DEAD
  - DEAD → ctrl of the restart team

  Everything else is forbidden. This is the same structural idea as PathCRF's masked CRF.
- **Emissions per frame:** a weighted sum of log-evidence from E1 to E5, with event bonuses at the
  L2 event frames.
- **Durations (semi-Markov):**
  - DEAD has a minimum length (stoppages last seconds);
  - ctrl and flight have **no long minimum**, because sub-second spells exist. The protection
    against flicker comes from the control-confirmation requirement in L2, not from smoothing.
- **Switch cost:** an opponent gain of control is only taken when its evidence beats a fixed
  penalty. This is the "uncertain → keep the current owner" rule, written into the decoder.
- **Decoding:** exact Viterbi per half, which is deterministic and offline. Changes land on the
  event frames.

The mapping to labels follows H0: a ball **in flight belongs to the team that played it** until the
other team gains control. This matches "possession stays with the last team" and the owner-field
semantics.

---

## 6. Parameters and where they may come from

The rules require every tuned value to come from external data or a documented physical prior.

| parameter | role | source |
|---|---|---|
| r_ctrl (possession zone) | control radius | prior **1.0–1.5 m** (Vidal-Codina 2022 optimum 0.5–1.0 m by provider; databallpy default 1.5 m), then tuned externally |
| r_duel | duel zone around the ball | prior **1.0 m** (Vidal-Codina 2022) |
| θ, Δv | touch = direction change or speed jump | prior **10°** and **1–5 m/s** (Vidal-Codina 2022; databallpy defaults 10° / 5 m/s); PathCRF's RDP uses 15° |
| position smoothing | before velocities | Savitzky–Golay, order 2, 7-frame window (Vidal-Codina 2022) |
| d_dwell | control confirmation | tuned externally; prior: short, since sub-second spells exist |
| d_still, minimum DEAD duration | dead ball | physical prior; tuned externally |
| maximum ball speed, maximum player speed | plausibility gates | physical priors (≈ 35 m/s, ≈ 10 m/s) |
| sensor weights w_E1…w_E5, switch penalty | fusion | **tuned externally** on spellF1 |
| PathCRF weights | E2 | released weights, unchanged (trained on Sportec only) |
| detector thresholds (FootAndBall) | L0 | published defaults |

**External tuning set:**
- **IDSSE / Sportec Open DFL**: 7 matches, **CC BY 4.0** (verified on figshare,
  10.6084/m9.figshare.28196177), loadable with `floodlight.io.datasets.IDSSEDataset` (MIT). It has
  per-frame `BallStatus` ("inactive when the match is interrupted by the referee") and
  `BallPossession` ("defined by the player in control of the ball"). These are the **same two
  fields our ground truth is derived from**, so labels are built exactly like the ground truth:
  `BallStatus=0` → D, else the `BallPossession` team.
- Metrica sample data **has no licence** (the GitHub repo has none). It is excluded until the
  organisers confirm we may use it. If they do, it is the closest match to the ground truth, since
  it comes from the same company and its event types fit H0.
- The same corruption as our data is applied: the ball removed on ~41 % of live frames in
  clustered gaps, fragmented and anonymised player slots, position noise.
- Everything is scored with the official `possession_metrics.py`.
- Caveat: PathCRF was trained on Sportec, so it is evaluated only on its held-out fold, or on the
  Metrica matches.

No parameter is set from this match: not from its ATD statistics, its ground truth, or its video.

---

## 7. Build order (each step ships a valid submission)

| step | adds | expected effect |
|---|---|---|
| 1 | L0 (minimal) + E1 + E4 (ball and kinematic dead-ball) + L3 with a ctrl/DEAD-only state set | beats the baseline mainly by removing "ball missing → D" and flicker |
| 2 | L2 confirmation rule + flight states + restart-team laws | correct turnover timing, no deflection switches, correct `D → team` |
| 3 | E5 tags + E3 shape | better behaviour in long ball gaps |
| 4 | E2 PathCRF (needs the 22-lane L0) | turnovers inside ball gaps, duel disambiguation |
| 5 | video ball re-detection in L0 | fewer gaps for E1 |

Every step is an **ablation** on the external dev set, kept only if it improves spellF1 there
beyond the ~0.04 noise band. The public window is never used to choose.

## 8. Ideal version (not feasible by 2026-11-17)

Retrain PathCRF **with the ball as an input** (the code already supports `ball_feature=True`). The
ball would be randomly masked on ~41 % of frames during training on Sportec plus Metrica, and
outside-node and DEAD states would be added. One learned model would then replace E1, E2 and most of
L3. Training takes hours per fold on a GPU, so this is a post-deadline direction.

## 9. Implementation shortcuts (verified)

| need | reuse | licence |
|---|---|---|
| E1 touch and control detection | port `databallpy/features/player_possession.py`. It needs only x/y columns and the ball velocity, with no identities. Add Vidal-Codina's duel zone and loss rule, plus a fallback for a missing ball (the original fails on NaN) | MIT |
| E4 restart and set-piece triggers | Vidal-Codina 2022 supplement tolerances: kickoff 3–5 m, corner 3 m, throw-in 0.5 m, goal kick 0.5 m, free kick = default | from the paper (no code) |
| E4 dead ball from players only | features from Lang et al. 2022, Sci. Rep. 12:16291 (team speed collapse etc.; up to 92 % in/out-of-play accuracy) | from the paper (no code) |
| IDSSE loader | `floodlight.io.datasets.IDSSEDataset` | MIT |
| L3 decoder | hand-rolled explicit-duration Viterbi: each state is expanded into a chain of K_min sub-states, about 40 lines of numpy. The HSMM libraries are archived or broken (hsmmlearn GPL and archived, pyhsmm 2017, edhsmm archived) | ours |

## 10. Open questions

1. Is H0 right about **what** switches the owner? Ask the organisers whether we may use Metrica's
   unlicensed sample data, whose events would show it directly.
2. Does the owner switch at the **touch** or at the **confirmation** of control? H0 says the
   touch. Check against the public window's label semantics by reading, not by fitting.
3. The ball in flight to an opponent who never controls it and then goes out: H0 keeps the
   original owner until DEAD. That matches "loose ball stays", but needs confirming.
