# 06 — Research pass 2: video ball detection, possession code, licences, tooling

Two parallel web-research passes (2026-11-15). Licences and the databallpy defaults were re-checked
directly on GitHub and figshare. Claims marked *unverified* were not confirmed at the source.

## A. Recovering the ball from the tactical video

Verdict: **one time-boxed attempt (≈ 4–6 h), no more.**

| rank | model | why | catch |
|---|---|---|---|
| 1 | **FootAndBall** ([repo](https://github.com/jac99/FootAndBall), [paper](https://arxiv.org/abs/1912.05445)), **MIT** (verified), weights in the repo (verified) | trained on ISSIA-CNR: fixed long-shot Full-HD cameras at 25 fps, the closest domain to our tactical camera; full 1920×1080 input, no tiling; ball AP 0.909; 37 fps on a GTX 1060 → ≈ 1 h per match on a GPU | old dependencies (PyTorch 1.10); single-frame |
| 2 | **WASB-SBDT** ([repo](https://github.com/nttcom/WASB-SBDT), [paper](https://arxiv.org/abs/2311.05237)), **MIT** (verified), soccer weights on Google Drive | 3-frame heatmap model, robust to blur; soccer F1 88.3 at 4 px | no custom-video script; its 288×512 input would shrink our ball, so it needs native-resolution crops around the interpolated position |
| ✗ | Roboflow `sports` YOLOv8 ball model, soccana (YOLO11n) | — | **AGPL** (Ultralytics) weights, unsuitable for our public repo; broadcast-trained; slow when tiled |
| ✗ | TrackNetV3/V4 | — | no soccer weights |
| ✗ | SoccerNet sn-gamestate | — | heavy, broadcast, no ball output (*unverified*) |

**Risks:**
- In a full-pitch view the ball may be only 3–5 px.
- Our gaps are the hardest frames: occlusions, duels, aerial balls.
- A recovered position still leaves duels ambiguous.

**Rules:**
- Use the published confidence thresholds.
- The go/no-go is decided on **external footage**.
- On our match only automatic, label-free sanity flags are allowed: the share of gap frames with a
  detection that is on the pitch and physically plausible, and agreement with the tracked ball
  where it exists. They must not be used to set thresholds.
- **No overlaying detections on our video to judge them** (organisers' clarification).

## B. Possession, touch and control detection code

| tool | licence | what it does | use for us |
|---|---|---|---|
| **databallpy** `features/player_possession.py` | MIT (verified) | Vidal-Codina-style player possession: nearest player within `pz_radius`; a run becomes a gain if the ball velocity changes by > `bv_threshold` or the direction by > `ba_threshold`° | **port it** for E1. It needs only x/y and the ball velocity, no identities. Missing: a duel zone and handling of a missing ball (NaN fails the gain test) |
| databallpy `add_team_possession` | MIT | derived from event data | not usable |
| floodlight | MIT (verified) | no possession model; parses DFL `BallPossession`/`BallStatus`; `IDSSEDataset` loader | **loader** for the tuning set |
| kloppy | BSD-3 | parses provider possession and status fields; nothing for Metrica | loader only |
| unravelsports | MPL-2.0 | nearest player within 25 m, no hysteresis | low value |
| tryolabs/soccer-video-analytics | MIT | video; team switch after 20 consecutive frames (hysteresis) | idea only |
| **Vidal-Codina et al. 2022** | no public code | the full rule set, below | use the parameters as **priors** |

**Vidal-Codina 2022 parameters**, from the paper and its supplement:

| parameter | value |
|---|---|
| possession-zone radius | 0.5–1.5 m (optimum 0.5 or 1.0 m depending on provider) |
| duel zone | 1 m around the ball; ≥ 2 opponents inside → duel, which overrides possession |
| smoothing | Savitzky–Golay, order 2, 7 frames |
| gain | direction change > 10° or speed change > 1–5 m/s, dated at the first control frame |
| loss | ball leaves the zone with displacement > 5–10 cm and the player is absent from the next control frame; regaining with nobody else in between keeps possession |
| restart triggers | kickoff 3–5 m, penalty 2/2/4 m, corner 3 m, throw-in 0.5 m, goal kick 0.5 m, free kick = default |

## C. Dead ball

- **Lang et al. 2022**, *Sci. Rep.* 12:16291
  ([PMC9522646](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9522646/)): in-play vs interrupted
  from **player tracking only**. Up to 92 % frame accuracy (102 Bundesliga matches); no code
  found. Its features (e.g. team speed collapse) are the template for E4.
- **Borghesi et al. 2023**, *ESWA*: a TCN for alive/dead, then possession (86.2 % possession
  accuracy). Code not checked.
- **Whistle audio:** no football repo found. RoboCup detectors (bit-bots, HULKs band-power FFT)
  exist; a 2–4 kHz band-energy detector is simple to write, but that band is *unverified*.

## D. External data licences

| dataset | licence | ball state / possession fields | decision |
|---|---|---|---|
| **IDSSE / Sportec Open DFL** (7 matches) | **CC BY 4.0** (verified on figshare 10.6084/m9.figshare.28196177) | `BallStatus` and `BallPossession` per frame, the same semantics as our ground truth | **primary tuning set** |
| Metrica sample data | **none** (verified: no licence file) | derivable from events | **excluded**; ask the organisers |
| SkillCorner open data | MIT repo; credit requested | per-frame possession; no ball state; 10 fps broadcast | optional secondary |
| PFF FC WC2022 | no licence text found (*unverified*) | event-driven | avoid |

## E. Segmentation tooling

The HSMM libraries are unusable: hsmmlearn is GPL and archived, pyhsmm's last release was 2017,
and edhsmm is archived. ruptures (BSD-2) has no per-state duration priors. **Decision:** hand-roll
an explicit-duration Viterbi (each state expanded into K_min sub-states, about 40 lines of numpy).

## Impact on the framework

All of the above is integrated into [../framework.md](../framework.md):
- the parameter priors (§6);
- IDSSE as the tuning set, with the Metrica data excluded (§6);
- the implementation shortcuts (§9).
