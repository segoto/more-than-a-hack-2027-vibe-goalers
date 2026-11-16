# Scoring mechanics: macroF1 and spellF1

What `EVALUATION.md` states but doesn't work through: how each metric is computed in
`evaluation/possession_metrics.py`, how it reacts to specific errors, and what that implies for the
design. Worked numeric cases are in [cases.md](cases.md); all of them come from the official code
via `python "pathcrf&oth/scripts/metric_cases.py"`.

Notation: frames at 25 fps; *spell* = possession = maximal run of `H` or of `A` within a half.

---

## macroF1 (tie-break)

`confusion` → `scored_confusion` → `macro_f1`:

1. 3×4 confusion matrix: GT rows `H/A/D` (GT `X` frames are dropped), prediction columns
   `H/A/D/X`.
2. Per class k: precision = TP / predicted-k, recall = TP / GT-k, F1 = 2PR / (P+R).
3. macroF1 = unweighted mean of F1_H, F1_A, F1_D.

- A predicted `X` on a graded frame is a false negative for the GT class, and never a false
  positive.
- Class-unweighted, so constant predictions score near the floor rather than at the class share.
- **Blind spots:** it scores frames independently, so it barely registers
  - uniform lag (only frames near boundaries change),
  - fragmentation (flicker leaves most frames correct),
  - short spells (a 2 s spell is ~50 frames out of ~159k).

  Case C5 in [cases.md](cases.md): 0.910 macroF1 with 147 predicted spells against 10 true.
- Noise band ≈ 0.01. The effective sample is the number of segments, not frames.

## spellF1 (ranking)

`spell_scores(gt, fill_abstentions(pred))`:

| step | function | behaviour |
|---|---|---|
| 1. fill abstentions | `fill_abstentions` | each `X` takes the last non-`X` label in the same half (back-fill at the head). After this there is no `X` |
| 2. extract spells | `possession_spells` | maximal `H`/`A` runs per half; `D` runs are excluded but split spells (`H D H` = 2 spells) |
| 3. pairwise IoU | `spell_overlaps` | only **same-team** overlapping pairs; IoU = \|∩\| / \|∪\| in frames |
| 4. matching | `matched_gt_flags` | greedy over pairs sorted by IoU descending; **one-to-one** (a GT spell and a predicted spell are each consumed once); stop when IoU < threshold |
| 5. score | `match_spells`, `spell_scores` | TP = matched, FP = unmatched predicted, FN = unmatched GT; F1 = 2TP / (2TP+FP+FN); mean over IoU ∈ {0.3, 0.4, 0.5, 0.6, 0.7} |

Consequences of the construction:

- Every spell has equal weight regardless of duration.
- **Partial credit comes only from the threshold average:** a pair with IoU 0.45 counts at 2 of
  the 5 thresholds.
- Constant or random predictions score exactly 0.
- Noise band ≈ 0.04 on the full match.

---

## Boundary behaviour

**Frames are never reassigned between spells.** Each frame belongs to exactly one predicted spell,
IoU is pairwise, and matching is one-to-one. Therefore:

| situation | effect |
|---|---|
| `H→A` boundary late by δ | predicted H gains δ frames (its union grows); predicted A loses δ (its intersection shrinks). **Both neighbours pay** |
| `H→D` or `D→H` boundary late | only the spell side pays; `D` is not scored by spellF1 (only by macroF1) |
| predicted spell overlaps two GT spells of the same team | it can match only one; the other overlap is discarded. **Spill-over never helps the neighbour** |
| missed stoppage between same-team spells | two GT spells vs one predicted: IoU ≈ len/total with each, at most one match. One of the costliest errors (case B5: 0.267) |
| spurious short flip inside a spell | one spell becomes three predicted spells → 2 FP, and the surviving piece has IoU ≤ ~0.5 (case A3: 0.30) |
| `X` across a boundary | becomes a boundary late by the gap length (step 1) |

### Lag tolerance as a function of spell length

For a spell of length L shifted by δ: `IoU = (L − δ) / (L + δ)`. It is counted at threshold t iff
`L ≥ δ·(1+t)/(1−t)`:

| t | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 |
|---|---|---|---|---|---|
| minimum L | 1.86 δ | 2.33 δ | 3.00 δ | 4.00 δ | 5.67 δ |
| at δ = 1 s | 1.9 s | 2.3 s | 3.0 s | 4.0 s | 5.7 s |

With a 1 s error, spells over ~5.7 s are unaffected; spells between ~1.9 and 5.7 s lose part of
their credit; spells under ~1.9 s are lost entirely. That's why `EVALUATION.md`'s "1 s late →
0.6539" is much worse than it looks for long possessions: the match contains many short ones.

Other error shapes on a GT spell of length L:

| error | IoU |
|---|---|
| starts late by a, ends late by b | (L − a) / (L + b) |
| extended by a and b | L / (L + a + b) |
| truncated by a and b | (L − a − b) / L |

---

## Design implications

1. **Possession count is a first-class target.** FP (fragmentation) and FN (merging) cost the same
   per spell. Track the predicted count (the validator prints it).
2. **No `D` for "ball not observed".** It splits spells (A4, C6). `D` must come from stoppage
   evidence only.
3. **Inside a spell, hold the team under uncertainty.** Holding is free (A5, C7); a wrong flip
   costs about 0.7 of that spell's value (A3).
4. **At a transition, commit to a boundary estimate.** Never leave it to `X` forward-fill (B7).
5. **Boundary precision matters most on short spells and at spell-to-spell transitions.** Those
   are charged on both sides; spell-to-dead edges are charged once (B1 vs B4).
6. **Stoppage recall matters even when the same team restarts** (B5).
7. **Fill abstentions ourselves.** Same spellF1, better macroF1, and the fill can use the *next*
   label before a transition, which `X` can't.
8. **The public 5-minute window can't rank variants.** 17 spells; one miss moves spellF1 by ~0.06.
   Use it for format/alignment checks only (`docs/ORGANIZERS_CLARIFICATION.md`).
