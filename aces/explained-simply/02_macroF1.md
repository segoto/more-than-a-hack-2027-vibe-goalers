# 02 — macroF1: "check every page"

macroF1 is a teacher who looks at **every picture one by one** and asks: "is this letter right?"
It is the **tie-break**: it only matters if two teams have the same spellF1.

## Step 1 — three piles: H, A and D

The teacher looks at each letter (H, A and D) separately. Take `H`:

- **Precision for H** — *"When you said H, were you right?"*
  You wrote `H` on 100 pictures; 80 of them really were `H`. Precision = 80/100 = **0.8**.
- **Recall for H** — *"Of all the real H pictures, how many did you find?"*
  There were 160 real `H` pictures; you found 80. Recall = 80/160 = **0.5**.

### The fishing net

- **Precision**: of everything in your net, how much is fish (and not old boots)?
- **Recall**: of all the fish in the pond, how many are in your net?

A huge net catches all the fish (recall high) but also lots of boots (precision low). A tiny net
catches only fish (precision high) but very few of them (recall low). You want both.

## Step 2 — F1 squeezes the two into one number

```
F1 = 2 × precision × recall / (precision + recall)
```

It's a special kind of average that is **only high when both are high**. With precision 0.8 and
recall 0.5: F1 = 2 × 0.8 × 0.5 / 1.3 = **0.615** (a normal average would say 0.65 — F1 is
stricter).

## Step 3 — "macro" = every letter counts the same

We get F1 for `H`, F1 for `A`, F1 for `D`, and take the plain average:

```
macroF1 = (F1_H + F1_A + F1_D) / 3
```

Even if `D` pictures are fewer (or more) than `H` pictures, each letter gets one third of the score.
That stops a lazy answer from looking good: writing `D` everywhere gives F1 = 0 for `H` and `A`, so
macroF1 is tiny (case C2 on page 06: **0.078**).

## What does `X` ("I don't know") do here?

On a marked picture, `X` counts as **a miss** — like a wrong answer for the real letter. It lowers
recall. It never counts as a false `H`, `A` or `D`, because `X` isn't one of them.

## What macroF1 is bad at seeing

Because it looks at pictures one by one, it **doesn't notice turns**:

1. **Being a bit late.** If every change of turn is 1 second late, only a few pictures near each
   change are wrong; all the pictures in the middle of turns are still right. (Case C4: macroF1
   still **0.938**.)
2. **Flickering.** If you flip to the wrong team for a tiny moment every few seconds, most pictures
   are still right. (Case C5: macroF1 **0.910**, while it invents **147 turns instead of 10**.)
3. **Missing short turns.** A 2-second turn is only 50 pictures out of many thousands. Missing it
   costs almost nothing here. (Case C8: macroF1 **0.984** even with two turns completely missed.)

That is exactly why the organisers rank on **spellF1** instead.

## How much difference is "real"?

Pictures next to each other are almost always the same, so the match really has a few hundred
"chunks", not 158,857 independent pictures. The organisers measured that differences **smaller
than about 0.01** in macroF1 are just noise.
