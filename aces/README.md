# `aces` — research branch

## Purpose of this branch

Everything we learned **before writing the pipeline**: how the challenge is scored, what "dead
ball" and "possession" should mean in code, whether ball-free possession models (PathCRF and
similar) can fill the 41% of frames where the ball is missing, and how to validate without breaking
the rules. It's meant to be read before the action plan and to feed the technical document.

Nothing here touches match data. Every example is synthetic and scored by the official
`evaluation/possession_metrics.py`. The original challenge docs at the repo root are unchanged.

## What's in it

| folder | for whom | what |
|---|---|---|
| [`explained-simply/`](explained-simply/README.md) | everyone, no background needed | spellF1 and macroF1 explained as to a five-year-old, with every example case (A1–A7, B1–B7, C1–C8) worked step by step |
| [`findings/`](findings/) | the people building the pipeline | the technical findings, 01–05 (below) |
| [`scripts/metric_cases.py`](scripts/metric_cases.py) | anyone | re-runs every example through the official metric code: `python aces/scripts/metric_cases.py` |

## Findings in brief

1. **The ranking metric rewards whole possessions, not frames**
   ([findings/01](findings/01_problem_and_metrics.md)). spellF1 matches each true possession to at
   most one predicted possession by temporal overlap, averaged over five strictness levels.
   - A 2 s flicker inside a 40 s possession drops spellF1 from 1.00 to 0.30.
   - A flickery output can score 0.91 per frame and 0.03 on possessions.
   - Late boundaries cost both neighbouring possessions; overlap never carries over to the next
     one; missing a stoppage between two same-team possessions is among the costliest errors.
   - `X` means "same as before", not "no answer".

2. **Dead ball is an interval with two edges to detect**
   ([findings/02](findings/02_dead_ball_and_possession.md)):
   - *play stops*: ball out of bounds, collective deceleration, goal;
   - *play restarts*: a still ball at a restart spot, then collective acceleration, plus
     set-piece shapes and Smart Tagging `SET PIECES`.

   Never output `D` just because the ball is missing.

3. **Possession, in code:** it changes at the **first touch** of an opponent that is followed by
   **control**. Control means a short dwell with the ball, or a completed pass to a teammate. Loose
   balls stay with the last team. The public ground truth contains possessions under 1 s, so the
   organisers' "a few seconds" proxy is too strict. Boundaries go back to the first touch: we work
   offline and can look ahead to confirm control.

4. **PathCRF (KDD 2026) is relevant but not a drop-in**
   ([findings/03](findings/03_pathcrf_evaluation.md)). It infers who has the ball from players
   alone, and its pretrained weights are trained only on external Bundesliga data. But it needs:
   - 22 gap-free trajectories (we have 46 anonymous slots with gaps);
   - the stretches where play is live, supplied by us;
   - our own "control" rule, because it counts every touch.

   It complements the tracked ball (precise but present on only 59% of frames). The team's
   [`docs/PATHCRF_ANALYSIS.md`](../docs/PATHCRF_ANALYSIS.md) reaches the same facts; this branch
   also keeps running the unchanged weights open as an optional parallel track.

5. **Other methods** ([findings/04](findings/04_related_methods.md)): no Hugging Face model does
   this. The closest are Ball Radar, TranSPORTmer (reimplemented inside PathCRF) and MIDAS
   (trajectory models), Vidal-Codina 2022 (rule-based control zones), and T-DEED (video on-ball
   action spotting). Identity re-ID is not worth it: possession needs the team, not the player.

6. **Design and validation** ([findings/05](findings/05_integration_design.md)): fuse the ball,
   PathCRF, team shape and Smart Tagging into a 3-state H/A/D decoder with minimum durations.
   **All tuning happens on external matches** (Sportec Open DFL, Metrica samples), with labels
   derived the same way as the challenge's and synthetic noise added. Licences must be verified
   first.

## Rules this branch follows

[`docs/ORGANIZERS_CLARIFICATION.md`](../docs/ORGANIZERS_CLARIFICATION.md) overrides `RULES.md`. In
particular:
- no tuning or calibrating on this match;
- no checking our output against the video;
- the public 5 minutes are only for format checks;
- no match data in any AI service.

Where an idea from our earlier notes crossed one of these lines, the findings were corrected and
say so. For example, comparing PathCRF with the ball on this match is allowed only as a sanity flag,
never to set weights.

## Environment note

On one of our machines, Windows Application Control blocks a pandas DLL under Python 3.14. The
script falls back to a placeholder pandas module, since the metric functions it calls are
numpy-only. The real scorer (`run_evaluation.py`) needs a working pandas, so use a venv or another
interpreter.
