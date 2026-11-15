# 02 — Dead ball and the definition of possession

## What the public ground truth shows

Segments of `evaluation/gt/BAR-ATH_possession_gt_public.csv` (public, shipped in the repo; used
here only to understand what the labels mean, as CHALLENGE.md directs. **No number in this repo is
taken from it** — no threshold, duration or count. Per the team's hard constraint 6 (`CLAUDE.md`),
the public window is never used to train, tune, calibrate or choose):

```
A   6.64s | H   8.08s | A  2.84s | H 41.64s | A  7.44s | D  5.52s | H 28.60s
A   3.24s | H  42.44s | A 20.00s | H  0.76s | A 16.04s | H  1.32s | A  3.60s
D  20.44s | A  35.72s | H  3.48s | D 18.32s | A  7.56s | D 14.48s | H 11.84s
```

1. **Sub-second possessions exist** (0.76 s, 1.32 s). "Keeps the ball a few seconds" is looser than
   the GT's real behaviour.
2. **Stoppages are long** here (5.5–20.4 s). Expect shorter ones elsewhere (quick free kicks).
3. **Both `A→D→H` and `A→D→A` occur.** The same team restarting = two possessions.
4. **No gaps:** the half opens directly on the kickoff team; after `D` the restarting team owns the
   ball from the first frame.
5. GT is mechanical from corrected tracking → we target Metrica's ownership semantics.

## Dead ball (`D`)

`D` = one interval **[play stops, restart touch)**. Two edges, two detectors.

| | start edge (play stops) | end edge (play restarts) |
|---|---|---|
| causes | ball out (throw-in/corner/goal kick), whistle (foul, offside), goal, injury, end of half | throw-in, corner, goal kick, free kick, kickoff, penalty, drop ball |
| tracking signature | ball leaves [0,1]² or is last seen on a line then lost; collective deceleration | still ball at a restart spot, then moves; collective acceleration |

**Evidence, strongest first**

1. **Ball kinematics** (when visible): out-of-bounds; ball stationary > ~1 s at a restart spot
   (corner arc, touchline, 6-yard box, centre spot).
2. **Player kinematics** (always available — the backbone): mean speed collapse, no sprints;
   set-piece shapes:
   - corner: both teams packed in one box, one player at the corner
   - throw-in: one player on the touchline
   - goal kick: GK in 6-yard box, attackers retreating
   - kickoff: two compact halves, two players at the centre
   - free kick: a wall ≈ 9 m from a still ball

   Then collective acceleration at the restart.
3. **Smart Tagging:** `SET PIECES` (type; team except throw-ins = `N/A`), `GOALS` → `D` until
   `Kick Off (After Goal)`. Intervals are *phases*, not the D window — check locally where tag
   edges fall relative to the ball becoming still.
4. **Video/audio (optional):** referee whistle (~2–4 kHz tonal burst) if the tactical video has
   audio; video action spotting (OUT, THROW IN, FREE KICK — see 04).

**Decoding:** per-frame P(dead) → 3-state H/A/D HSMM/Viterbi with minimum durations (D: a few
seconds). **Restart team** = nearest player when the ball starts moving, or by law (throw-in /
corner / goal kick go to the team that did *not* touch last; after a goal, the conceding team
kicks off).

**Traps**
- `D` because the ball is missing → splits possessions. Never.
- A missed `A→D→A` stoppage merges two possessions.
- 2nd-half pre-kickoff `D` (110,808–113,741): the kickoff detector must find it; the FAQ number is
  a check, not a constant (no frame-specific constants derived from this match).
- Don't set the minimum D length from the public 5.5 s — that is tuning on the public window.

## Possession

### Organiser statements → implications

| statement | implication |
|---|---|
| ball alive ⇒ one team always in possession | no "contested" state |
| loose/contested ball stays with last team | switch only on opponent *control* |
| restarts have a clear possessor | `D → restart team` |
| change requires **controlled** possession | the crux |
| not a change: touch w/o control, non-intercepting deflection, aerial duel w/o subsequent control | brief opponent contact ≠ switch |
| proxies: holds a few seconds / >2 passes | too strict vs GT (0.76 s spells) |
| GT = corrected tracking's owning team | target = "who the tracking system considers in control" |

### Operational definition

> Possession passes from T to T′ at the **first touch** of a T′ player that is followed by T′
> **control**, where control is either
> (a) **dwell** — a T′ player within ~1–1.5 m of the ball, ball moving *with* him, for a short
> dwell (order 0.3–0.6 s); or
> (b) **completed pass** — the T′ touch is followed by a next *controlling* touch by another T′
> player (catches one-touch interceptions).
>
> **Not control:** opponent near the ball while its trajectory is barely changed and the next
> controller is T again; high/fast ball with no subsequent control.

- Offline ⇒ confirm with look-ahead, then **back-date the boundary to the first touch**.
- Default = stickiness: the current team holds through ball gaps and loose balls.
- Under uncertainty prefer *no switch*: a false 2 s flicker shreds a long spell; true short spells
  leave strong traces (interception, pass chain, shape flip).

### When the ball is invisible (41%)

- Team shape: possessing team stretches/advances, defenders compact/drop; shapes flip within ~2 s
  after a turnover.
- Pressing: several players of T converging on one T′ player ⇒ T′ has it.
- Smart Tagging: `BUILD UP` / `PROGRESSION` / `CREATING CHANCES` name the team **with** the ball;
  `DEFENDING IN …` names the team **without** it (invert!).
- Last-seen / re-appearance: ball vanished near T, reappears near T′ ⇒ switch inside the gap,
  placed by the player proximity in the gap, not by forward-fill.
- **Ball-free possessor inference** — PathCRF / Ball Radar (see 03, 04).
