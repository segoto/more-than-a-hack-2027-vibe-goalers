# 05 — Integration design: fusing the ball, PathCRF and Smart Tagging

A design sketch, not yet the action plan. It answers: *how would PathCRF be joined to the tracked
ball to decide possession?*

## Architecture

```
 ATD (players, ball) ──► clean & smooth ──► lanes (22 continuous) ──► PathCRF ──► P_path(H|A|out | t)
        │                                                                              │
        ├──► ball-visible control detector (zone + dwell + pass chain) ──► P_ball(H|A | t)   │
        ├──► dead-ball detector (ball out/still, kinematics, set-piece shapes) ──► P(D | t)  │
        └──► team shape / pressing features ──► P_shape(H|A | t)                       │
 Smart Tagging ──► phase team priors, set-piece/goal restarts ──► P_tag(·| t)          │
                                                                                       ▼
                         per-frame log-evidence for {H, A, D}, weighted by availability
                                                │
                                                ▼
              3-state hidden semi-Markov decoder (Viterbi per half)
              - min durations: H/A short (sub-second spells exist), D a few seconds
              - transitions: H↔A (turnover), H/A→D (stoppage), D→H/A (restart team)
              - switch cost: a turnover needs evidence, not a flicker
                                                │
                                                ▼
                       frame,label CSV (no X inside play; we fill ourselves)
```

## Fusion rule

Per frame, combine log-probabilities with weights that depend on what's available:

```
score_t(k) = w_ball(t)·log P_ball(k) + w_path(t)·log P_path(k)
           + w_shape·log P_shape(k) + w_tag·log P_tag(k)        k ∈ {H, A}
score_t(D) from the dead-ball detector and PathCRF's out-of-play mass
```

- `w_ball` high when the ball is visible *and* close to a player (unambiguous); ~0 when missing.
- `w_path` scaled by PathCRF's confidence; and lower when lanes were mostly invented (long fills).
- Weights are **set from football reasoning and from dev-set matches**, never from the public 5 min.

The decoder, not the per-frame scores, decides boundaries; the evidence only needs to be
calibrated roughly.

## Boundary placement

The decoder works at 25 fps on fused evidence. When a turnover falls inside a ball gap, the
change point will land where PathCRF's possessor switches team — typically more precise than the
gap midpoint. When the ball is visible, the ball-proximity first touch dominates.

## Validation without breaking the rules

| check | data | allowed? |
|---|---|---|
| pipeline correctness (alignment, format, label meaning) | public 5 min | format/alignment only; pending confirmation (`docs/QUESTIONS_FOR_ORGANIZERS.md`) |
| choose between design variants / set weights | **other matches**: Sportec (7), Metrica samples (3) with GT derived like the challenge's (`ball_state` → D, `ball_owning_team` → H/A), with synthetic noise (ball dropped ~41% in clustered gaps, fragmented tracks) | yes — external data, licence to verify and document |
| PathCRF vs ball agreement on this match | our two algorithm outputs, no labels | **only as an automatic sanity flag** — using it to set weights = calibrating on the provided game → **no** |
| tuning, calibrating or choosing on public 5 min | — | **no** |
| comparing our output with the video | — | **no** (organisers' clarification) |

Score dev matches with the official `possession_metrics.py` so the numbers mean the same thing.
Use `--bootstrap 1000`; differences under ~0.04 spellF1 are noise.

## What to build first (pending the action plan)

1. Local data-profiling script (ball-gap lengths, objects per frame per team, tag-edge alignment).
2. Classical pipeline end-to-end → a valid submission, scored on the public window for
   correctness only.
3. In parallel: PathCRF environment + lane builder + inference on one dev match.
4. Fuse, validate on dev matches, freeze, regenerate, validate the exact file.
