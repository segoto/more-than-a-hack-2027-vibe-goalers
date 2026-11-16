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

## Metrics

How macroF1 and spellF1 are computed, how they respond to lag, fragmentation, merging and `X`, the
lag-tolerance table and the design implications are in
[../explained-simply/README.md](../explained-simply/README.md), with worked cases in
[../explained-simply/cases.md](../explained-simply/cases.md).
