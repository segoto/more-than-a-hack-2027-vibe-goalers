"""Descriptive statistics of the tactical ATD, printed as aggregates only.

    python analysis/describe_atd.py
    python analysis/describe_atd.py --data-dir /path/to/mtah2027

Reads data/tactical/BAR-ATH_tactical_atd.{xml,txt} locally (paths from games.asset_paths) and
prints summary numbers: file format checks, ball and player coverage per match block, ball-gap
lengths, track-slot fragmentation, speeds and plausibility flags, and ball-to-nearest-player
distances. Nothing here prints a frame-level row, so the output can be shared without leaking the
dataset. It is descriptive only: no parameter of any model is fitted from these numbers.

numpy only, same environment as the scorer. Expect a minute or two: it streams 199319 lines and
holds the whole match in memory (~110 MB as float32).
"""

import argparse
import os
import sys
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from games import GAME, GAMES, half_video_blocks, require, source_frames  # noqa: E402
from starter.baseline import team_of_each_track, team_names  # noqa: E402

# Params
# Raw ATD line: "<frame_id>:<x,y,s>;<x,y,s>;...:<ball>", NaN for a missing observation.
FIELD_SEP = ":"
GROUP_SEP = ";"
VALUE_SEP = ","
PLAYER_FIELDS = 3  # x, y (normalised 0-1) and speed (m/s), per DATA.md

FPS = GAMES[GAME]["fps"]
PLAYERS_PER_TEAM = 11

# Plausibility thresholds -- physical priors, not values read off this match.
# Elite sprinters in football top out around 10-11 m/s (~36-38 km/h); 12.5 m/s leaves margin.
MAX_PLAYER_SPEED = 12.5
# The hardest recorded shots are ~55 m/s; typical strong shots and long passes stay under ~35 m/s.
# Anything above 45 m/s between consecutive frames is almost certainly a tracking jump.
MAX_BALL_SPEED = 45.0

# Ball-to-nearest-player distance bands, in metres, for the proximity summary.
DISTANCE_BANDS = (1.0, 2.0, 5.0, 10.0)
# Ball-gap length buckets, in frames (25 = 1 s).
GAP_BUCKETS = ((1, 1), (2, 5), (6, 25), (26, 125), (126, 750), (751, None))


def load_raw(raw_path, n_slots, n_frames):
    """Whole ATD as arrays: players (frames, slots, 3), ball (frames, 2), plus format counters."""
    players = np.full((n_frames, n_slots, PLAYER_FIELDS), np.nan, dtype=np.float32)
    ball = np.full((n_frames, 2), np.nan, dtype=np.float32)
    seen = np.zeros(n_frames, dtype=bool)
    fmt = {"lines": 0, "malformed": 0, "id_out_of_range": 0, "duplicate_id": 0,
           "bad_player_width": 0, "ball_fields": {}}

    with open(raw_path) as handle:
        for line in handle:
            fmt["lines"] += 1
            parts = line.rstrip("\n").split(FIELD_SEP)
            if len(parts) != 3:
                fmt["malformed"] += 1
                continue
            index = int(parts[0]) - 1  # frame_id counts from 1, video frames from 0
            if not 0 <= index < n_frames:
                fmt["id_out_of_range"] += 1
                continue
            if seen[index]:
                fmt["duplicate_id"] += 1
            seen[index] = True

            values = np.array(parts[1].replace(GROUP_SEP, VALUE_SEP).split(VALUE_SEP),
                              dtype=np.float32)
            if values.size != n_slots * PLAYER_FIELDS:
                fmt["bad_player_width"] += 1
            else:
                players[index] = values.reshape(n_slots, PLAYER_FIELDS)

            ball_values = parts[2].strip().split(VALUE_SEP)
            fmt["ball_fields"][len(ball_values)] = fmt["ball_fields"].get(len(ball_values), 0) + 1
            if len(ball_values) >= 2:
                ball[index] = np.array(ball_values[:2], dtype=np.float32)

    return players, ball, seen, fmt


def runs(mask):
    """(starts, lengths) of every maximal run of True in a 1-D boolean array."""
    padded = np.concatenate(([False], mask, [False])).astype(np.int8)
    step = np.diff(padded)
    starts = np.flatnonzero(step == 1)
    return starts, np.flatnonzero(step == -1) - starts


def pct(values, qs=(5, 50, 95)):
    """Percentiles of the finite values, as a short string."""
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return "n/a"
    return "  ".join("p{}={:.2f}".format(q, v) for q, v in zip(qs, np.percentile(values, qs)))


def share(part, whole):
    return 100.0 * part / whole if whole else float("nan")


def section(title):
    print("\n" + title)
    print("-" * len(title))


def match_blocks(n_frames):
    """[(name, first, last)] covering the whole video: pre-match, halves, halftime, post-match."""
    (_, s1, e1), (_, s2, e2) = half_video_blocks(GAME)
    return [("before match", 0, s1 - 1), ("1st half", s1, e1), ("halftime", e1 + 1, s2 - 1),
            ("2nd half", s2, e2), ("after match", e2 + 1, n_frames - 1)]


def describe_format(fmt, seen, n_frames, n_slots, teams, home, away):
    section("File and format")
    print("lines read            {}".format(fmt["lines"]))
    print("expected video frames {}".format(n_frames))
    print("frames with a record  {}  ({} missing)".format(int(seen.sum()), int((~seen).sum())))
    print("malformed lines       {}".format(fmt["malformed"]))
    print("frame_id out of range {}   duplicated frame_id {}".format(
        fmt["id_out_of_range"], fmt["duplicate_id"]))
    print("lines with wrong player width {}".format(fmt["bad_player_width"]))
    print("ball group field counts {}".format(dict(sorted(fmt["ball_fields"].items()))))
    print("track slots {}: H ({}) {} slots, A ({}) {} slots".format(
        n_slots, home, int((teams == 0).sum()), away, int((teams == 1).sum())))


def describe_blocks(blocks, present, ball_ok, teams):
    section("Coverage per match block")
    n_tracked = present.sum(axis=1)
    n_home = present[:, teams == 0].sum(axis=1)
    n_away = present[:, teams == 1].sum(axis=1)
    header = "{:<13}{:>8}{:>8}{:>10}{:>10}{:>8}{:>8}{:>8}{:>9}"
    print(header.format("block", "frames", "ball%", "trk mean", "trk p50", "H mean",
                        "A mean", ">22 %", "team>11%"))
    for name, first, last in blocks:
        cut = slice(first, last + 1)
        frames = last - first + 1
        over_team = (n_home[cut] > PLAYERS_PER_TEAM) | (n_away[cut] > PLAYERS_PER_TEAM)
        print("{:<13}{:>8}{:>8.1f}{:>10.2f}{:>10.0f}{:>8.2f}{:>8.2f}{:>8.2f}{:>9.2f}".format(
            name, frames, share(ball_ok[cut].sum(), frames), n_tracked[cut].mean(),
            np.median(n_tracked[cut]), n_home[cut].mean(), n_away[cut].mean(),
            share((n_tracked[cut] > 2 * PLAYERS_PER_TEAM).sum(), frames),
            share(over_team.sum(), frames)))


def describe_ball_gaps(halves, ball_ok):
    section("Ball gaps inside graded frames (runs of frames without ball)")
    lengths = []
    for _, first, last in halves:
        _, half_lengths = runs(~ball_ok[first:last + 1])
        lengths.append(half_lengths)
    lengths = np.concatenate(lengths)
    missing = lengths.sum()
    print("gaps {}   missing frames {}".format(lengths.size, int(missing)))
    print("length in frames: {}".format(pct(lengths, (50, 90, 99))))
    print("longest gap {} frames ({:.1f} s)".format(int(lengths.max()), lengths.max() / FPS))
    print("{:<16}{:>8}{:>18}".format("length (frames)", "gaps", "% missing frames"))
    for low, high in GAP_BUCKETS:
        sel = (lengths >= low) & (lengths <= high if high else True)
        label = "{}-{}".format(low, high) if high else ">{}".format(low - 1)
        print("{:<16}{:>8}{:>18.1f}".format(label, int(sel.sum()),
                                            share(lengths[sel].sum(), missing)))


def describe_slots(present, graded, teams):
    section("Track slots (tracklets, not people)")
    frag_lengths, rows = [], []
    for slot in range(present.shape[1]):
        _, lengths = runs(present[:, slot])
        frag_lengths.append(lengths)
        rows.append((slot + 1, "HA"[teams[slot]], share(present[graded, slot].sum(), graded.sum()),
                     lengths.size, np.median(lengths) / FPS if lengths.size else 0.0))
    frag_lengths = np.concatenate(frag_lengths)
    print("slots never used {}".format(sum(1 for r in rows if r[3] == 0)))
    print("fragments {}   length in s: {}".format(
        frag_lengths.size, pct(frag_lengths / FPS, (10, 50, 90))))
    print("fragments shorter than 1 s: {:.1f}%".format(
        share((frag_lengths < FPS).sum(), frag_lengths.size)))
    print("\n{:>5}{:>6}{:>14}{:>11}{:>16}".format("slot", "team", "% graded on", "fragments",
                                                  "median frag s"))
    for row in rows:
        print("{:>5}{:>6}{:>14.1f}{:>11}{:>16.1f}".format(*row))


def describe_speeds(players, ball, graded, pitch):
    section("Speeds and plausibility (graded frames)")
    length, width = pitch
    reported = players[graded, :, 2]
    print("player speed reported (m/s): {}".format(pct(reported, (50, 90, 99, 100))))
    print("  above {} m/s: {:.3f}% of observations".format(
        MAX_PLAYER_SPEED, share((reported > MAX_PLAYER_SPEED).sum(),
                                np.isfinite(reported).sum())))

    pair = graded[:-1] & graded[1:]
    step = np.diff(players[:, :, :2], axis=0)[pair]
    derived = np.hypot(step[..., 0] * length, step[..., 1] * width) * FPS
    print("player speed from positions (m/s): {}".format(pct(derived, (50, 90, 99, 100))))
    print("  jumps above {} m/s: {} ({:.3f}%)".format(
        MAX_PLAYER_SPEED, int((derived > MAX_PLAYER_SPEED).sum()),
        share((derived > MAX_PLAYER_SPEED).sum(), np.isfinite(derived).sum())))

    ball_step = np.diff(ball, axis=0)[pair]
    ball_speed = np.hypot(ball_step[:, 0] * length, ball_step[:, 1] * width) * FPS
    print("ball speed from positions, consecutive frames (m/s): {}".format(
        pct(ball_speed, (50, 90, 99, 100))))
    print("  jumps above {} m/s: {} ({:.3f}%)".format(
        MAX_BALL_SPEED, int((ball_speed > MAX_BALL_SPEED).sum()),
        share((ball_speed > MAX_BALL_SPEED).sum(), np.isfinite(ball_speed).sum())))


def describe_positions(players, ball, ball_ok, graded):
    section("Positions (graded frames, normalised 0-1)")
    b = ball[graded & ball_ok]
    outside = (b < 0) | (b > 1)
    print("ball outside [0,1]: {:.2f}% of visible-ball frames".format(
        share(outside.any(axis=1).sum(), b.shape[0])))
    p = players[graded, :, :2].reshape(-1, 2)
    p = p[np.isfinite(p[:, 0])]
    print("players outside [0,1]: {:.2f}% of observations".format(
        share(((p < 0) | (p > 1)).any(axis=1).sum(), p.shape[0])))

    edges = np.array([0.0, 1 / 3, 2 / 3, 1.0])
    zone_x = np.clip(np.digitize(b[:, 0], edges) - 1, 0, 2)
    zone_y = np.clip(np.digitize(b[:, 1], edges) - 1, 0, 2)
    print("\nball occupancy by thirds (% of visible-ball graded frames)")
    print("{:>12}{:>10}{:>10}{:>10}".format("", "x 1/3", "x 2/3", "x 3/3"))
    for row in range(3):
        cells = [share(((zone_x == col) & (zone_y == row)).sum(), b.shape[0]) for col in range(3)]
        print("{:>12}{:>10.1f}{:>10.1f}{:>10.1f}".format("y {}/3".format(row + 1), *cells))


def describe_proximity(players, ball, ball_ok, graded, teams, pitch):
    section("Ball to nearest tracked player (graded frames with ball)")
    length, width = pitch
    sel = graded & ball_ok
    dx = (players[sel, :, 0] - ball[sel, None, 0]) * length
    dy = (players[sel, :, 1] - ball[sel, None, 1]) * width
    distance = np.hypot(dx, dy)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        nearest = np.nanmin(distance, axis=1)
    has_player = np.isfinite(nearest)
    print("frames {}   with no player tracked {}".format(sel.sum(), int((~has_player).sum())))
    print("distance (m): {}".format(pct(nearest, (10, 50, 90, 99))))
    for band in DISTANCE_BANDS:
        print("  within {:>4.1f} m: {:.1f}%".format(
            band, share((nearest[has_player] <= band).sum(), has_player.sum())))
    nearest_slot = np.argmin(np.where(np.isfinite(distance), distance, np.inf), axis=1)[has_player]
    nearest_team = teams[nearest_slot]
    print("nearest player is H on {:.1f}%, A on {:.1f}%".format(
        share((nearest_team == 0).sum(), nearest_team.size),
        share((nearest_team == 1).sum(), nearest_team.size)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default=None, help="overrides MTAH_DATA_DIR / ./data")
    args = parser.parse_args()

    meta_path, raw_path = require(["atd_meta", "atd_raw"], GAME, args.data_dir)
    n_frames = source_frames("tactical", GAME)
    pitch = GAMES[GAME]["pitch"]
    teams = team_of_each_track(meta_path)
    home, away = team_names(meta_path)

    print("reading {} ...".format(os.path.basename(raw_path)))
    players, ball, seen, fmt = load_raw(raw_path, teams.size, n_frames)

    present = np.isfinite(players[:, :, 0])
    ball_ok = np.isfinite(ball[:, 0])
    halves = half_video_blocks(GAME)
    graded = np.zeros(n_frames, dtype=bool)
    for _, first, last in halves:
        graded[first:last + 1] = True

    describe_format(fmt, seen, n_frames, teams.size, teams, home, away)
    describe_blocks(match_blocks(n_frames), present, ball_ok, teams)
    describe_ball_gaps(halves, ball_ok)
    describe_slots(present, graded, teams)
    describe_speeds(players, ball, graded, pitch)
    describe_positions(players, ball, ball_ok, graded)
    describe_proximity(players, ball, ball_ok, graded, teams, pitch)


if __name__ == '__main__':
    main()
