# 01 — The problem and how it is scored

Source: every `.md` in the challenge repo plus `evaluation/possession_metrics.py` (the metric
specification; if docs and code disagree, the code wins).

## The task

One match, **FC Barcelona (H) vs Athletic Club (A)**, LaLiga 2024-25 MD2. For each of the
**199,319** frames of the tactical video output one label:

| label | meaning |
|---|---|
| `H` | home in possession, ball alive |
| `A` | away in possession, ball alive |
| `D` | dead ball |
| `X` | abstain (or ungraded frame) |

Graded: video frames **11,185–90,651** and **110,808–190,197** (158,857 frames). The 2nd half is
graded from 110,808 but kicks off at **113,742** — those 2,934 frames are all `D`.

**Inputs:** tactical + broadcast video, automatic tracking (ATD, 46 anonymous track slots, team per
slot, ball missing on 41% of graded frames), Smart Tagging (638 automatic phase/set-piece
intervals), per-frame homography. Broadcast is not synchronised to tactical.

**Ground truth** is *mechanically derived from corrected tracking*: `D` where corrected tracking
marks the ball dead, otherwise the team it names as owner. Nothing smoothed. We are reproducing
Metrica's own corrected "ball state" and "owning team" semantics.

**Rules that bind the design.** [`docs/ORGANIZERS_CLARIFICATION.md`](../../docs/ORGANIZERS_CLARIFICATION.md)
overrides `RULES.md` and `FAQ.md`; `CLAUDE.md` lists the team's hard constraints.
- Any algorithm/model/external data allowed; organisers must be able to inspect it; the tech doc
  must explain it.
- **No hand labels or manually created data on this match**, for any purpose. Hand labels on
  *other* matches are fine (licence checked).
- **Train, tune and calibrate only on external data.** No pseudo-labels and no unsupervised or
  self-supervised learning on this match (the clarification removes what `RULES.md` allowed).
  Estimating parameters on this match's ATD or Smart Tagging is a grey zone → **NO GO** until
  confirmed.
- **No checking our output against the video.** Watching the video to understand possession is
  fine.
- No private GT, no human-produced data about this match (events, corrected tracking).
- The public 5 minutes are at most a **format/alignment check** — not training, tuning, calibrating
  or choosing between versions (even the check is pending confirmation,
  `docs/QUESTIONS_FOR_ORGANIZERS.md`).
- The repo must regenerate the *exact* file.
- No match data to AI services — including the coding assistant.

Baseline floor: `baseline_smooth50`, **spellF1 0.2433** (nearest player to ball + ±2 s majority).

## macroF1 — per-frame view (tie-break)

1. 3×4 confusion: GT rows H/A/D, prediction columns H/A/D/X.
2. Per-class F1 = harmonic mean of precision and recall.
3. Unweighted mean over H, A, D.

- Predicted `X` on a graded frame = a miss for that GT class (recall), never a false positive.
- Unweighted so "always D" scores ~0.1–0.16 rather than looking competent.
- Blind to timing (a 10-frame lag barely moves it), to fragmentation, and to short possessions.
- Noise band ≈ **0.01** (effective sample is segments, not frames).

## spellF1 — possession view (ranking)

1. **Fill abstentions:** `X` → previous non-X label in the same half (back-fill at half start).
2. **Spells:** maximal runs of `H` or `A`, computed per half. `D` runs are stoppages, not spells.
   `H H D D H H` is **two** possessions.
3. **IoU** for every *same-team* overlapping (GT, pred) pair:
   `IoU = |overlap| / |union|`.
4. **Greedy one-to-one matching** per threshold, IoU-descending; each spell used at most once.
   TP = matched, FP = unmatched predictions, FN = unmatched GT. F1 = 2TP / (2TP+FP+FN).
5. Mean of F1 at IoU **0.3, 0.4, 0.5, 0.6, 0.7**.

Range [0,1]; constant guess = 0. Noise band ≈ **0.04**.

### Toy cases (run `python aces/scripts/metric_cases.py`, group A)

| situation | spellF1 | F1 @ .3/.4/.5/.6/.7 |
|---|---|---|
| perfect | 1.00 | 1 1 1 1 1 |
| GT `H20s A3s H20s`, predicted all H (missed short interception) | **0.20** | .5 .5 0 0 0 |
| GT 40 s H, spurious 2 s **A** inside | **0.30** | .5 .5 .5 0 0 |
| same, spurious 2 s **D** inside | **0.40** | .67 .67 .67 0 0 |
| same, 2 s **X** inside | **1.00** | 1 1 1 1 1 |
| 10 s spell, 1 s late | 1.00 | 1 1 1 1 1 |
| 2 s H then 8 s A, transition 1 s late | 0.90 | 1 1 1 1 .5 |

### How late boundaries work (run `python aces/scripts/metric_cases.py`, group B)

Frames are **never reassigned** between spells. Each frame belongs to exactly one predicted spell;
IoU is pairwise; matching is one-to-one.

- A late `H→A` boundary **lengthens** the predicted H (its union grows) **and shortens** the
  predicted A (its intersection shrinks). Both neighbours pay.
- Cross-team overlap is never computed: frames of your H inside GT A are invisible except as extra
  union.
- A late `H→D` boundary costs only the H side (D is not a spell).
- **Spill-over into the next same-team spell is wasted**: once a predicted spell is matched, its
  other overlaps are discarded. Missing a stoppage between two same-team spells (`H D H` predicted
  as one `H`) → IoU ≈ 0.43 with each, matched to one at 0.3/0.4 only → spellF1 0.267.
- `X` across a transition = a transition late by the gap length.

Uniform lag δ on a spell of length L: `IoU = (L−δ)/(L+δ)`. It passes threshold t iff
`L ≥ δ(1+t)/(1−t)`:

| t | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 |
|---|---|---|---|---|---|
| min L | 1.86δ | 2.33δ | 3δ | 4δ | 5.67δ |
| δ = 1 s | 1.9 s | 2.3 s | 3 s | 4 s | 5.7 s |

### Design consequences

1. Never output `D` merely because the ball is missing (baseline's main error). Hold the team or
   write `X` inside possessions.
2. Possession *count* matters as much as frame accuracy; flicker = FPs, merges = FNs.
3. Short possessions need boundaries accurate to a fraction of a second; long ones tolerate ~1 s.
4. Missing a stoppage between same-team spells is one of the costliest errors.
5. At transitions, place the boundary explicitly — don't let `X` forward-fill carry the old team.
6. `X` vs writing the forward-fill yourself: identical on spellF1, worse on macroF1. Fill yourself
   (and you may fill with the *next* team before a transition, which `X` can't do).
