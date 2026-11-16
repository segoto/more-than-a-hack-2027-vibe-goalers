# 04 — Related methods and repositories

No Hugging Face model does ball-free possession or ball imputation on tracking data. What is on
the Hub is video detection (players/ball). The relevant work lives in research repos.

## A. Ball-free possessor / ball inference from player trajectories

| method | what | code / weights | fit |
|---|---|---|---|
| **PathCRF** (KDD 2026) | possessor + pass edges per step, CRF-consistent; out-of-play nodes | [repo](https://github.com/hyunsungkim-ds/pathcrf), **weights included**, MPL-2.0 | **best fit** — see 03 |
| **Ball Radar** (KDD 2023) | possessor classifier → ball trajectory regressor, Set Transformer + Bi-LSTM | [repo](https://github.com/hyunsungkim-ds/ballradar), no weights found; [paper](https://arxiv.org/abs/2306.08206) | PathCRF's predecessor; trains on Metrica sample data. Its *ball regressor* could fill ball positions in gaps if we ever need positions rather than possessors |
| **TranSPORTmer** (ACCV 2024) | one transformer for forecasting, imputation, ball inference, and a CLS token classifying pass/possession state | no official code found; **a reimplementation ships inside PathCRF** (`models/transportmer.py`); [paper](https://arxiv.org/abs/2410.17785) | comparable backbone, no reason to prefer it |
| **MIDAS / DBHP** (ECML-PKDD 2025) | imputes missing *player* trajectories (Set Transformer + derivative accumulation), evaluated on Metrica data | [repo](https://github.com/gkswns95/midas), no weights | a learned alternative for building PathCRF's gap-free lanes; heavier than interpolation |
| **Graph Imputer** (DeepMind, 2022) | off-screen player imputation, graph VAE | no public code | reference only |

## B. Rule-based possession / event detection from tracking (with ball)

| method | what | fit |
|---|---|---|
| **Vidal-Codina et al. 2022**, "Automatic event detection in football using tracking data" ([paper](https://arxiv.org/abs/2202.00804)) | possession zone of radius R around each player; "control frames" from ball-in-zone + duel logic; events from ball–player distance changes | **template for our "control" rule** on frames where the ball is visible: deterministic, explainable, no training |
| **databallpy** ([docs](https://databallpy.readthedocs.io/en/latest/features/team_and_player_possession.html)) | team possession (from synced events) and individual player possession from tracking | reference implementation of zone-based player possession; its team possession needs event data we can't use for this match |
| **kloppy** | loader; reads Metrica EPTS, Sportec, TRACAB uniformly | glue for building a dev set from open matches |

## C. Video-based on-ball action spotting (for gaps the tracking can't explain)

| method | what | fit |
|---|---|---|
| **T-DEED** (CVPR-W 2024, 1st in SoccerNet Ball Action Spotting 2024) | frame-precise spotting of on-ball actions from video | [repo](https://github.com/arturxe2/T-DEED). SoccerNet BAS 2024 grew from 2 to 12 classes (pass, drive, and others such as out-of-play and set-piece actions — confirm the exact list on the SoccerNet task page). Trained on broadcast, so tactical-camera domain shift. Strong evidence for **D edges** (out, throw-in, free kick) and touch times while the ball is lost in tracking |
| **SoccerNet BAS 2025 entries** ([results](https://arxiv.org/abs/2508.19182)) | refined T-DEED variants, e.g. the `dude.k` package | same; more effort |

## D. Tracking clean-up (identity)

| method | what | fit |
|---|---|---|
| **GTA-link** ([repo](https://github.com/sjc042/gta-link), [paper](https://arxiv.org/abs/2411.08216)) | appearance-based split/merge of tracklets | needs video re-ID crops; low value — team-level possession doesn't need identities |
| **Game-state reconstruction post-processing** ([paper](https://arxiv.org/abs/2504.06357)) | merge tracklets by jersey/team/re-ID with a physical-reachability check | the *reachability* check is the useful idea for our lane building (03 §4) |

## E. Open data usable as a development set (other matches — allowed)

| dataset | contents | use |
|---|---|---|
| **Sportec Open DFL** ([paper](https://www.nature.com/articles/s41597-025-04505-y)) | 7 matches, tracking with ball, events, `ball_state`, `ball_owning_team` | derive H/A/D labels the same way the challenge GT is derived; caution — PathCRF was trained on these (use the fold's held-out match) |
| **Metrica Sports sample data** (3 matches, one in the **same EPTS format** as our ATD) | tracking with ball + events | closest format to ours; synthesise our noise (drop the ball ~41% in clustered gaps, fragment tracks) |
| **SoccerNet** | video + labels | only if we go the video route |

## Ranking for our deadline

1. **Rule-based control (B) + HSMM decoder** — the critical path; no training, fully explainable.
2. **PathCRF (A)** — highest-value add-on, parallel track; needs lane building.
3. **Video spotting (C)** — only if someone has GPU time and the tactical video decodes cleanly.
4. **Identity re-ID (D)** — skip.
