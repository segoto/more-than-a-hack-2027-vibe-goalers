# 06 — Cases C1–C8: the two scores side by side

A made-up 4-minute piece of a match, with **10 turns and 2 pauses**, some long and some very short:

```
H 40s | A 8s | H 2s | A 30s | D 15s | H 25s | A 3s | H 20s | D 10s | A 35s | H 12s | A 40s
```

We make different kinds of mistakes and score each one with **both** teachers. Run:
`python aces/scripts/metric_cases.py` (group C).

| case | what we did | macroF1 | spellF1 | turns found / real |
|---|---|---|---|---|
| C1 | perfect | 1.000 | 1.000 | 10 / 10 |
| C2 | wrote `D` everywhere | 0.078 | 0.000 | 0 / 10 |
| C3 | wrote `H` everywhere | 0.190 | 0.000 | 1 / 10 |
| C4 | perfect, but everything 1 s late | 0.938 | 0.880 | 10 / 10 |
| C5 | perfect, but a 0.4 s flicker every 3 s | **0.910** | **0.028** | **147** / 10 |
| C6 | lost the ball 25 times (1–3 s each), wrote `D` there | 0.776 | 0.254 | 31 / 10 |
| C7 | the same lost moments, wrote `X` there | 0.917 | **1.000** | 10 / 10 |
| C8 | missed the 2 s and the 3 s turns | **0.984** | **0.700** | 6 / 10 |

## What each case teaches

**C2 and C3 — lazy answers.** Writing one letter everywhere scores 0 on spellF1: there are no real
turns in it to match. macroF1 gives a small number, not 0 — the organisers call this the "floor".
How small depends on how much of the match each letter covers; for the real match they say about
0.16.

**C4 — a little late everywhere.** Both scores drop a bit. macroF1 barely notices (0.938) because
most pictures sit in the middle of turns. spellF1 drops more (0.880) because the short turns (2 s,
3 s) fail the strict teachers.

**C5 — flicker: the big disagreement.** macroF1 says **0.910**, "great!". spellF1 says **0.028**,
"terrible!". Who is right? spellF1: our list claims the match had **147 turns** when it had 10. A
coach reading it would be completely misled. Each flicker cuts a turn into pieces, and every piece
is an invented turn.

**C6 vs C7 — what to write when we lose the ball.** Same moments, different letter:

- writing `D` (pause) cuts turns into pieces → 31 turns, spellF1 **0.254**;
- writing `X` ("same as before") keeps every turn whole → spellF1 **1.000**.

macroF1 also prefers `X` here (0.917 vs 0.776). Writing the previous team ourselves would be even
better for macroF1 (those pictures would count as right, not as misses) and the same for spellF1.

**C8 — missing short turns.** macroF1 hardly moves (**0.984**) because 5 seconds out of 4 minutes is
a tiny number of pictures. spellF1 drops to **0.700**: we found 6 turns instead of 10, and the turns
around each missed one became too long.

## The real-life version

The organisers' simple example program does exactly what C5 and C6 warn about: "the closest player
has the ball, else `D`", then a majority vote over a window to calm the flicker. Only the window
size changes between its four versions:

| version | macroF1 (full match) | spellF1 (full match) |
|---|---|---|
| no smoothing | 0.6532 | **0.0486** |
| ±1 s window | **0.6752** | 0.1996 |
| ±2 s window | 0.6724 | **0.2433** ← the score to beat |
| ±5 s window | 0.6356 | 0.2242 |

macroF1 moves by only 0.04 and prefers the ±1 s version. spellF1 moves by **five times** and prefers
±2 s. Smoothing helps because it removes flicker; too much smoothing starts erasing real short
turns.

And a warning: on the **5 public minutes** the ±5 s version looks best (0.4242 vs 0.3256), but on
the full match it is worse. Five minutes (17 turns) is far too few to choose anything with — one
missed turn moves the score by about 6 points. That's why we never use the public window to pick
between versions.
