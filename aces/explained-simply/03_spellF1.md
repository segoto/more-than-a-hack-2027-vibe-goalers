# 03 — spellF1: "find every turn"

spellF1 is a teacher who doesn't care about single pictures. She asks: **"Did you find each turn,
as a whole turn, at about the right time?"** Each turn counts **once**, whether it lasted 2 seconds
or 2 minutes — the way a coach counts possessions. **This score decides the ranking.**

It works in five steps.

---

## Step 1 — fill in the "I don't know"s

Before anything else, every `X` is replaced by **the last real letter you wrote before it** (in the
same half). If the half *starts* with `X`, it takes the first letter after.

```
you wrote:   H H X X X H A A
teacher reads: H H H H H H A A
```

So for this teacher `X` doesn't mean "I don't know". It means **"same as before"**.

- Inside a turn this is perfect: the turn stays in one piece.
- Right at a change of turn it's dangerous: the old team gets copied into the new team's time.

## Step 2 — cut both lists into turns

The teacher cuts the true list and our list into **turns** (also called *spells*): stretches of
`H`, or stretches of `A`. `D` stretches are pauses — **not turns** — but they separate turns.

```
truth:  D D H H H H A A H H H D D H H
            └─ H1 ─┘└A1┘└─H2─┘    └H3┘    → 4 true turns
```

## Step 3 — measure how much turns overlap (IoU)

Take a true turn and one of our turns **of the same team**. Lay them on top of each other like two
strips of paper:

```
truth:   |■■■■■■■■■■■■■■■■■■■■|
ours:         |■■■■■■■■■■■■■■■■■■■■|
              └──── overlap ─────┘
         └─────────── covered by either ──────┘
```

```
IoU = overlap / covered by either
```

- Exactly the same → IoU = 1
- Not touching at all → IoU = 0
- Example: truth is 250 pictures, ours is the same length but starts 25 pictures late.
  overlap = 225, covered = 275, IoU = 225/275 = **0.82**

Important: a **Barcelona** turn is only ever compared with **Barcelona** turns. Our `H` lying on
top of a true `A` is never measured — it just makes our `H` strip longer.

## Step 4 — find dance partners (one each!)

Now every true turn looks for **one** partner among our turns. Rules:

1. **Best overlaps dance first.** The teacher lists every pair from the highest IoU to the lowest.
2. **Each one dances with only one partner.** Once a true turn has a partner, it's taken; once one
   of our turns has a partner, it's taken too.
3. **The overlap must be good enough** (see step 5).

Then she counts:

| count | means |
|---|---|
| **TP** (true positives) | pairs that danced — turns we found |
| **FP** (false positives) | our turns left without a partner — turns we invented |
| **FN** (false negatives) | true turns left without a partner — turns we missed |

And the F1 for this round:

```
F1 = 2·TP / (2·TP + FP + FN)
```

Inventing turns (FP) and missing turns (FN) both hurt.

## Step 5 — five teachers, from kind to strict

"Good enough overlap" isn't one number. There are **five teachers**, each with her own minimum IoU:

| teacher | accepts a pair if IoU ≥ |
|---|---|
| very kind | 0.3 |
| kind | 0.4 |
| fair | 0.5 |
| strict | 0.6 |
| very strict | 0.7 |

Each teacher does step 4 with her own rule and gives an F1. **spellF1 is the average of the five.**

So a turn that's almost perfect (IoU 0.95) is accepted by all five teachers. A sloppy one (IoU 0.45)
is only accepted by the two kind ones — it's worth about 2/5 of a perfect find.

---

## Putting it together in one tiny example

Truth: Barcelona has the ball for 40 seconds. We wrote Barcelona, but for 2 seconds in the middle we
flickered to Athletic.

```
truth:  |HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH|        1 turn  (1000 pictures)
ours:   |HHHHHHHHHHHHHHHHHHHH|AA|HHHHHHHHHHHHHHHHH|       3 turns (500 + 50 + 450)
```

- Step 3: our first H overlaps the truth with IoU 500/1000 = **0.50**; our second H with
  450/1000 = **0.45**. Our A has no Athletic turn to compare with.
- Step 4/5, kind teachers (0.3, 0.4): the 0.50 pair dances. The truth turn is now taken, so our
  second H and our A are left alone. TP 1, FP 2, FN 0 → F1 = 2/(2+2) = **0.5**.
- Fair teacher (0.5): 0.50 is just enough → **0.5**.
- Strict teachers (0.6, 0.7): nobody is good enough → TP 0 → **0**.
- spellF1 = (0.5 + 0.5 + 0.5 + 0 + 0) / 5 = **0.30**.

A 2-second hiccup took the score from 1.00 to 0.30. That is the whole personality of this metric.
(It's case A3 — page 04 has it and six more.)

## Facts the organisers measured

| | spellF1 |
|---|---|
| perfect | 1.0000 |
| perfect but 1 picture late | 1.0000 (free) |
| perfect but 3 / 8 pictures late | 0.9818 / 0.8933 |
| perfect but 1 second late | 0.6539 |
| random letters, or the same letter everywhere | 0.0000 |

Differences **smaller than about 0.04** are noise on the full match.
