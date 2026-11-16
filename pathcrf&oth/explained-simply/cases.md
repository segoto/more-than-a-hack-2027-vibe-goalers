# Worked cases

Synthetic label sequences scored with the official `possession_metrics.py`:

```bash
python "pathcrf&oth/scripts/metric_cases.py"
```

Lengths are in frames (25 = 1 s). "F1 per t" lists F1 at IoU 0.3 / 0.4 / 0.5 / 0.6 / 0.7. Mechanics
are explained in [README.md](README.md).

## A. Cost of a single error

Each case is one stretch of live play with dead ball on either side.

| case | GT | prediction | spellF1 | F1 per t | why |
|---|---|---|---|---|---|
| A1 | any | identical | 1.00 | 1 1 1 1 1 | — |
| A2 | H 500, A 75, H 500 | H 1075 | **0.20** | .5 .5 0 0 0 | one predicted spell, IoU 0.465 with each GT H; matches one at t ≤ 0.4; GT A and the other H are FN |
| A3 | H 1000 | H 500, **A 50**, H 450 | **0.30** | .5 .5 .5 0 0 | IoUs 0.50 / 0.45; one match, 2 FP |
| A4 | H 1000 | H 500, **D 50**, H 450 | **0.40** | .67 .67 .67 0 0 | same split, only 1 FP (D is not a spell) |
| A5 | H 1000 | H 500, **X 50**, H 450 | **1.00** | 1 1 1 1 1 | X forward-filled → one H spell |
| A6 | H 250 | H 250 shifted +25 | 1.00 | 1 1 1 1 1 | IoU 225/275 = 0.82 |
| A7 | H 50, A 200 | H 75, A 175 | **0.90** | 1 1 1 1 .5 | H IoU 50/75 = 0.67 fails t = 0.7; A IoU 0.875 |

## B. Boundaries and matching

| case | GT | prediction | pairs (IoU) | spellF1 |
|---|---|---|---|---|
| B1 — H→A late 1 s | H 250, A 250 | H 275, A 225 | H 0.909, A 0.900 | 1.000 |
| B2 — short A shifted 1 s | H 500, A 50, H 500 | H 525, A 50, H 475 | H 0.952, H 0.950, **A 0.333** | **0.733** |
| B3 — short A, start late only | same | H 525, A 25, H 500 | H 1.0, H 0.952, **A 0.500** | **0.867** |
| B4 — H→D late 1 s | H 250, D 100, A 250 | H 275, D 75, A 250 | H 0.909, A 1.0 | 1.000 |
| B5 — missed stoppage | H 300, D 100, H 300 | H 700 | 0.429 and 0.429 with the **same** predicted spell | **0.267** |
| B6 — spill-over | H 300, D 50, H 300 | H 400, D 50, H 200 | 0.750 ✔, 0.667 ✔, 0.077 (discarded, both consumed) | 0.900 |
| B7 — X at transition | H 250, A 250 | H 240, **X 40**, A 220 | after fill: H 280 / A 220 → 0.893, 0.880 | 1.000 |

Notes:
- **B1 vs B4:** a spell-to-spell boundary error is charged to both spells; a spell-to-dead one only
  to the spell.
- **B2 → B3:** fixing one edge of a short spell raises its IoU from 0.33 to 0.50, which is +2
  thresholds.
- **B5:** the predicted spell is consumed by the first match (ties break by GT index); the second
  GT spell becomes FN. F1 = 2/3 at t ≤ 0.4, 0 above.
- **B6:** the 50 frames of predicted spell 1 inside GT spell 2 only enlarge spell 1's union.
  GT spell 2 is scored against predicted spell 2 alone.
- **B7:** equivalent to a 30-frame-late boundary. It's harmless here only because both spells are
  10 s long.

## C. macroF1 vs spellF1

Synthetic 4-minute stretch with 10 spells and 2 stoppages, including 2 s and 3 s spells:

```
H 40s | A 8s | H 2s | A 30s | D 15s | H 25s | A 3s | H 20s | D 10s | A 35s | H 12s | A 40s
```

| case | prediction | macroF1 | spellF1 | spells pred / GT |
|---|---|---|---|---|
| C1 | identical | 1.000 | 1.000 | 10 / 10 |
| C2 | constant D | 0.078 | 0.000 | 0 / 10 |
| C3 | constant H | 0.190 | 0.000 | 1 / 10 |
| C4 | everything 1 s late | 0.938 | 0.880 | 10 / 10 |
| C5 | 0.4 s team flip every 3 s of play | **0.910** | **0.028** | 147 / 10 |
| C6 | 25 random 1–3 s "ball lost" gaps labelled D | 0.776 | 0.254 | 31 / 10 |
| C7 | same gaps labelled X | 0.917 | **1.000** | 10 / 10 |
| C8 | the 2 s and 3 s spells missed (absorbed by neighbours) | **0.984** | **0.700** | 6 / 10 |

Notes:
- **C2/C3:** the macroF1 floor depends on class shares; it's ~0.16 on the real match
  (`EVALUATION.md`).
- **C4:** the lag is absorbed by the long spells and costs on the 2 s and 3 s ones (see the
  lag-tolerance table in [README.md](README.md)).
- **C5 and C8:** the metrics disagree in opposite directions:
  - fragmentation keeps macroF1 high and destroys spellF1;
  - merging short spells barely moves macroF1 but loses 4 spells' worth of spellF1.
- **C6 vs C7:** the same missing-ball gaps cost 0.75 spellF1 as `D` and nothing as `X`. Writing
  the forward-filled team explicitly would also recover the macroF1 lost to `X`.
