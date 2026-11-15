# 04 — Cases A1–A7: what one mistake costs

Each case is one short piece of play with a pause on either side. We make **one** kind of mistake
and watch spellF1. Run them yourself: `python aces/scripts/metric_cases.py` (group A).

Reminder: 25 pictures = 1 second. The five numbers are the five teachers' F1 at IoU
0.3 / 0.4 / 0.5 / 0.6 / 0.7.

| case | what happened | spellF1 | five teachers |
|---|---|---|---|
| A1 | perfect | **1.00** | 1 1 1 1 1 |
| A2 | missed a 3-second interception | **0.20** | .5 .5 0 0 0 |
| A3 | 2-second flicker to the other team | **0.30** | .5 .5 .5 0 0 |
| A4 | 2-second flicker to "paused" (`D`) | **0.40** | .67 .67 .67 0 0 |
| A5 | 2 seconds of "I don't know" (`X`) | **1.00** | 1 1 1 1 1 |
| A6 | a 10-second turn, 1 second late | **1.00** | 1 1 1 1 1 |
| A7 | 2-second turn then 8-second turn, change 1 second late | **0.90** | 1 1 1 1 .5 |

---

## A1 — perfect

Every turn is found exactly: every pair has IoU 1, every teacher gives 1. **spellF1 = 1.00.**

## A2 — we missed a short interception

```
truth: |HHHHHHHHHHHHHHHHHHHH|AAA|HHHHHHHHHHHHHHHHHHHH|   20 s H, 3 s A, 20 s H → 3 turns
ours:  |HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH|   43 s H              → 1 turn
```

- Our one long H overlaps the first true H: 500 / 1075 = **0.465**. Same with the second true H.
- Our H can't be compared with the true A (different team).
- Kind teachers (0.3, 0.4): our H dances with one true H. It is then taken, so the other true H and
  the true A have no partner. TP 1, FP 0, FN 2 → F1 = 2/(2+0+2) = **0.5**.
- Fair and strict teachers (≥ 0.5): 0.465 is not enough → **0**.
- spellF1 = (0.5 + 0.5 + 0 + 0 + 0)/5 = **0.20**.

**Lesson:** missing one small turn doesn't cost "one small turn". It breaks the turns on **both
sides** too, because our one long strip can only dance once.

## A3 — a 2-second flicker to the other team

```
truth: |HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH|        40 s H → 1 turn
ours:  |HHHHHHHHHHHHHHHHHHHH|AA|HHHHHHHHHHHHHHHHH|       → 3 turns
```

Worked fully on page 03: IoUs 0.50 and 0.45, only one can dance, two of our turns are invented.
**spellF1 = 0.30.**

**Lesson:** a tiny wrong flip in the middle of a long turn cuts it into pieces. Pieces are invented
turns.

## A4 — the same flicker, but to "paused"

```
ours:  |HHHHHHHHHHHHHHHHHHHH|DD|HHHHHHHHHHHHHHHHH|       → 2 turns (D is not a turn)
```

- Our first H: IoU 0.50, second H: 0.45. Only one dances.
- TP 1, FP 1, FN 0 → F1 = 2/(2+1) = **0.67** for teachers 0.3, 0.4, 0.5; strict ones give 0.
- spellF1 = (0.67 × 3)/5 = **0.40**.

**Lesson:** writing `D` when we merely *lost sight of the ball* is almost as bad as writing the
wrong team. The organisers' simple example program (the "baseline") does exactly this, which is
one reason its score is low.

## A5 — the same 2 seconds, but "I don't know"

```
ours:  |HHHHHHHHHHHHHHHHHHHH|XX|HHHHHHHHHHHHHHHHH|
teacher reads: X → "same as before" = H
       |HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH|       → 1 turn, perfect
```

**spellF1 = 1.00.** (macroF1 still counts those 50 `X` pictures as misses.)

**Lesson:** inside a turn, when we're unsure, keeping the same team (or `X`) is free. Guessing can
only hurt.

## A6 — a 10-second turn, 1 second late

```
truth: |..........HHHHHHHHHH|
ours:  |...........HHHHHHHHHH|
```

IoU = 225/275 = **0.82**, above even the 0.7 teacher. **spellF1 = 1.00.**

**Lesson:** long turns forgive a bit of lateness.

## A7 — a short turn, change 1 second late

```
truth: |HH|AAAAAAAA|      2 s H, 8 s A
ours:  |HHH|AAAAAAA|      change 1 s late
```

- H: overlap 50, covered 75 → IoU **0.67**. Fails the 0.7 teacher only.
- A: overlap 175, covered 200 → IoU **0.875**. Everyone accepts.
- Teachers 0.3–0.6: both found → 1. Teacher 0.7: TP 1, FP 1, FN 1 → 2/4 = **0.5**.
- spellF1 = (1+1+1+1+0.5)/5 = **0.90**.

**Lesson:** the same 1-second lateness that was free in A6 now costs something, because the turn is
short. Page 05 shows exactly how short is "too short".
