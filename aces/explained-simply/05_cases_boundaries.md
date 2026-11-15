# 05 — Cases B1–B7: being late, merging, and taken partners

The question these cases answer: **when we put a change of turn too late, what happens to the extra
pictures? Do they count for the next turn?**

**Short answer: no.** Every picture belongs to exactly one of our turns. Moving the change later
makes our turn **before** it longer and our turn **after** it shorter. Nothing is ever handed over,
and every turn dances only once.

Run them: `python aces/scripts/metric_cases.py` (group B). Positions are in pictures, counted from
the start of the piece of play.

---

## B1 — change from H to A, 1 second late

```
truth:  |====== H 250 ======|====== A 250 ======|
ours:   |====== H 275 =========|==== A 225 =====|
                            ^^^ 25 late pictures
```

| pair | overlap | covered | IoU |
|---|---|---|---|
| true H vs our H | 250 | 275 | **0.909** — the late pictures make *our* H too long |
| true A vs our A | 225 | 250 | **0.900** — the late pictures are *missing* from our A |

**One late change hurts both neighbours.** Here both are still above 0.7, so spellF1 = **1.00**,
but only because both turns are 10 seconds long.

## The "how short is too short" rule

If a turn of length **L** is moved late by **δ** pictures (start and end both late):

```
IoU = (L − δ) / (L + δ)
```

A teacher with minimum **t** accepts it only if **L ≥ δ × (1 + t) / (1 − t)**:

| teacher (t) | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 |
|---|---|---|---|---|---|
| turn must be at least | 1.86 δ | 2.33 δ | 3 δ | 4 δ | 5.67 δ |
| if δ = 1 second | 1.9 s | 2.3 s | 3 s | 4 s | 5.7 s |

So with 1 second of lateness: turns longer than **5.7 s** are safe; turns between **1.9 s and
5.7 s** lose some teachers; turns shorter than **1.9 s** are lost completely. That is why the
organisers' "1 second late = 0.65" happens: real matches have many short turns.

Other shapes of mistake:

| our mistake | IoU |
|---|---|
| starts late by a, ends late by b | (L − a) / (L + b) |
| too long on both ends (a and b) | L / (L + a + b) |
| too short on both ends (a and b) | (L − a − b) / L |

## B2 — a 2-second A turn, everything 1 second late

```
truth:  |=== H 500 ===|A 50|=== H 500 ===|
ours:   |=== H 525 =====|A 50|== H 475 ==|
```

- H turns: IoU 0.952 and 0.95 — fine.
- A turn: overlap 25, covered 75 → IoU **0.333**. Only the 0.3 teacher accepts it.
- Teacher 0.3: all 3 found → 1. Teachers 0.4–0.7: 2 found, 1 invented, 1 missed →
  2·2/(4+1+1) = **0.67**.
- spellF1 = (1 + 0.67 × 4)/5 = **0.733**.

## B3 — the same short A, start late but end on time

```
ours:   |=== H 525 =====|A25|=== H 500 ===|
```

- A: overlap 25, covered 50 → IoU **0.5**. Teachers 0.3, 0.4, 0.5 accept.
- spellF1 = (1+1+1+0.67+0.67)/5 = **0.867**.

**Lesson:** on short turns, getting even **one edge** right is worth a lot.

## B4 — late change into a pause: only one side pays

```
truth:  |=== H 250 ===|D 100|=== A 250 ===|
ours:   |=== H 275 =====|D75|=== A 250 ===|
```

- H: IoU 250/275 = 0.909. A: untouched, 1.0.
- The shrunken `D` has no score in spellF1 (pauses aren't turns). **spellF1 = 1.00.**

**Lesson:** a mistake at a turn-to-pause edge is charged **once**; a mistake at a turn-to-turn edge
is charged **twice** (B1).

## B5 — we missed a pause between two Barcelona turns

```
truth:  |=== H 300 ===|== D 100 ==|=== H 300 ===|     2 turns
ours:   |================ H 700 ================|     1 turn
```

- Our H overlaps the first true H: 300/700 = **0.429**; the second: also **0.429**.
- Our H can dance **only once**. On a tie the first true turn wins. The second true turn is missed.
- Teachers 0.3, 0.4: TP 1, FN 1 → 2/3 = **0.67**. Teachers 0.5+: 0.429 is too low → 0.
- spellF1 = (0.67 + 0.67)/5 = **0.267**.

**Lesson:** this is one of the most expensive mistakes. Example in real football: the ball goes out
for a throw-in and the **same** team throws it in. If we don't see the pause, two turns become one.

## B6 — the extra pictures in the next turn are wasted

```
truth:  |=== H 300 ===|D 50|===== H 300 =====|
ours:   |====== H 400 ======|D|=== H 200 ===|
```

All pairs the teacher lists:

| pair | IoU | what happens |
|---|---|---|
| true H#1 – our H#1 | 0.750 | dance ✔ |
| true H#2 – our H#2 | 0.667 | dance ✔ (except for the 0.7 teacher) |
| true H#2 – our H#1 | 0.077 | ✘ both already have partners |

Our first H runs 50 pictures into the second true H. Those pictures **don't help the second true
turn at all**: they only make our first strip longer. The second true turn is judged only against
our second strip, which started late (0.667).

spellF1 = (1+1+1+1+0.5)/5 = **0.90**.

## B7 — "I don't know" right at the change

```
truth:  |=== H 250 ===|=== A 250 ===|
ours:   |== H 240 ==|X 40|== A 220 ==|      the real change is 10 pictures into our X
teacher reads X as H →
        |==== H 280 =====|== A 220 ==|      = a change 30 pictures late
```

IoUs 0.893 and 0.88, so spellF1 = **1.00** here (long turns). But with a short turn next to it, this
would cost exactly like B2.

**Lesson:** `X` at a change is the same as being late by the whole length of the `X`. When the
ball reappears with the other team, it's better to **put the change at our best guess** inside the
gap than to let "same as before" drag the old team across.
