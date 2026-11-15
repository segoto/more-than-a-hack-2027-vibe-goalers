# How we are scored — explained simply

This folder explains, as if to a five-year-old, how the challenge gives us a score: what
**macroF1** and **spellF1** are, how they work step by step, and every example case we reviewed.
No football analytics or maths background needed.

Every number in these pages was produced by the **official scoring code**
(`evaluation/possession_metrics.py`) on small made-up examples. You can re-run all of them:

```bash
python aces/scripts/metric_cases.py
```

## Read in this order

| page | what you learn |
|---|---|
| [01_the_game.md](01_the_game.md) | what we must produce: one letter per picture of the match |
| [02_macroF1.md](02_macroF1.md) | the "check every page" score, and why it is only the tie-break |
| [03_spellF1.md](03_spellF1.md) | the "find every turn" score that decides the ranking: spells, overlap (IoU), partners, five teachers |
| [04_cases_one_mistake.md](04_cases_one_mistake.md) | cases A1–A7: what one single mistake costs |
| [05_cases_boundaries.md](05_cases_boundaries.md) | cases B1–B7: being late, merging, partners that are already taken, "I don't know" at a hand-over |
| [06_cases_macro_vs_spell.md](06_cases_macro_vs_spell.md) | cases C1–C8: the two scores side by side, and why they disagree |
| [07_what_it_means_for_us.md](07_what_it_means_for_us.md) | the rules of thumb for building our system |

## The little dictionary

| word | simple meaning |
|---|---|
| **frame** | one picture of the video. 25 pictures = 1 second |
| **label** | the letter we write for one picture: `H`, `A`, `D` or `X` |
| **H** | Barcelona (home) has the ball and the game is running |
| **A** | Athletic (away) has the ball and the game is running |
| **D** | "dead ball": the game is paused (ball out, foul, goal…) |
| **X** | "I don't know" |
| **possession / spell / turn** | a stretch of pictures in a row where the same team has the ball, with no pause in between |
| **ground truth / truth** | the organisers' correct answer, which we never see (except 5 public minutes) |
| **prediction** | what our system writes |
| **IoU** | "how much do two stretches overlap", a number from 0 (not at all) to 1 (exactly the same) |
| **threshold** | the minimum overlap a teacher accepts |
| **precision** | of the things I said, how many were right |
| **recall** | of the things that really happened, how many I found |
| **F1** | one number that is only high when precision **and** recall are both high |
