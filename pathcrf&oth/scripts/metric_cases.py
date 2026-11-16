"""Every metric example in pathcrf&oth/explained-simply/cases.md, scored by the official metric code.

    python "pathcrf&oth/scripts/metric_cases.py"

Builds small synthetic label sequences (no match data, no ground truth -- every sequence here is
invented) and scores them with evaluation/possession_metrics.py exactly as run_evaluation.py does:
macro-F1 on the raw labels, spell-F1 after forward-filling abstentions.

Three groups:
  A. spellF1 toy cases      -- one short stretch of play, what a single mistake costs
  B. boundary / IoU cases   -- late transitions, merges, one-to-one matching, X at a hand-over
  C. macroF1 vs spellF1     -- a synthetic 4-minute half where the two metrics disagree

Frames are at 25 fps, so 25 frames = 1 second.

pandas is imported by possession_metrics only for reading CSVs. If it cannot be imported (on one
of our machines Windows Application Control blocks a pandas DLL), a placeholder is used -- the
functions called here are numpy-only, so the numbers are identical.
"""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "evaluation"))

try:
    import pandas  # noqa: F401
except Exception:  # ImportError, or an OS-level DLL block
    sys.modules["pandas"] = types.ModuleType("pandas")

import numpy as np  # noqa: E402
import possession_metrics as pm  # noqa: E402

H, A, D, X = pm.H, pm.A, pm.D, pm.X
FPS = 25
PAD = 100  # 4 s of dead ball either side, so every toy case sits inside one graded stretch


def seq(*parts):
    """seq((H, 250), (A, 50)) -> 250 frames of H then 50 of A."""
    return np.concatenate([np.full(n, code, dtype=np.int8) for code, n in parts])


def padded(*parts):
    return seq((D, PAD), *parts, (D, PAD))


def pad_array(codes):
    edge = np.full(PAD, D, dtype=np.int8)
    return np.concatenate([edge, codes, edge])


def scores(gt, pred):
    runs = pm.valid_runs(gt)
    spells = pm.spell_scores(gt, pm.fill_abstentions(pred, runs), runs)
    macro = pm.macro_f1(pm.scored_confusion(pm.confusion(gt, pred)))
    return spells, macro


def per_iou(spells):
    return " ".join("{:.2f}".format(v["f1"]) for v in spells["per_iou"].values())


def show_spells(codes, runs, offset):
    return [(a - offset, b - offset, "HA"[k]) for a, b, k in pm.possession_spells(codes, runs)]


def group_a():
    print("A. spellF1 toy cases  (F1 at IoU 0.3 / 0.4 / 0.5 / 0.6 / 0.7)")
    print("-" * 86)
    gt1 = padded((H, 500), (A, 75), (H, 500))
    gt2 = padded((H, 1000))
    gt3 = padded((H, 250))
    gt4 = padded((H, 50), (A, 200))
    cases = [
        ("A1 perfect", gt1, gt1),
        ("A2 missed 3 s interception (all H)", gt1, padded((H, 1075))),
        ("A3 40 s H, a 2 s A flicker inside", gt2, padded((H, 500), (A, 50), (H, 450))),
        ("A4 40 s H, a 2 s D flicker inside", gt2, padded((H, 500), (D, 50), (H, 450))),
        ("A5 40 s H, 2 s of X inside", gt2, padded((H, 500), (X, 50), (H, 450))),
        ("A6 10 s spell, predicted 1 s late", gt3, seq((D, PAD + 25), (H, 250), (D, PAD - 25))),
        ("A7 2 s H then 8 s A, change 1 s late", gt4, padded((H, 75), (A, 175))),
    ]
    for name, gt, pred in cases:
        spells, _ = scores(gt, pred)
        print("{:<44} spellF1 {:.3f}   {}".format(name, spells["mean_f1"], per_iou(spells)))
    print()


def group_b():
    print("B. boundary / IoU cases")
    print("-" * 86)
    cases = [
        ("B1 H->A change 25 frames (1 s) late",
         seq((H, 250), (A, 250)), seq((H, 275), (A, 225))),
        ("B2 short 2 s A, whole spell shifted 1 s late",
         seq((H, 500), (A, 50), (H, 500)), seq((H, 525), (A, 50), (H, 475))),
        ("B3 short 2 s A, start 1 s late, end on time",
         seq((H, 500), (A, 50), (H, 500)), seq((H, 525), (A, 25), (H, 500))),
        ("B4 H->D change 1 s late (only H pays)",
         seq((H, 250), (D, 100), (A, 250)), seq((H, 275), (D, 75), (A, 250))),
        ("B5 missed stoppage between two H spells",
         seq((H, 300), (D, 100), (H, 300)), seq((H, 700))),
        ("B6 spill-over into the next H spell is wasted",
         seq((H, 300), (D, 50), (H, 300)), seq((H, 400), (D, 50), (H, 200))),
        ("B7 X across the change = a late change",
         seq((H, 250), (A, 250)), seq((H, 240), (X, 40), (A, 220))),
    ]
    for name, gt_core, pred_core in cases:
        gt, pred = pad_array(gt_core), pad_array(pred_core)
        runs = pm.valid_runs(gt)
        filled = pm.fill_abstentions(pred, runs)
        g = pm.possession_spells(gt, runs)
        p = pm.possession_spells(filled, runs)
        pairs = pm.spell_overlaps(g, p)
        spells, _ = scores(gt, pred)
        print(name)
        print("   truth spells     ", show_spells(gt, runs, PAD))
        print("   predicted spells ", show_spells(filled, runs, PAD))
        print("   pairs (IoU, truth#, pred#)", [(round(i, 3), a, b) for i, a, b in pairs])
        print("   F1 per IoU {}   spellF1 = {:.3f}".format(per_iou(spells), spells["mean_f1"]))
    print()


def synthetic_half():
    """A made-up 4-minute stretch: 10 possessions and 2 stoppages, short and long spells."""
    plan = [(H, 40), (A, 8), (H, 2), (A, 30), (D, 15), (H, 25), (A, 3), (H, 20), (D, 10),
            (A, 35), (H, 12), (A, 40)]
    return seq(*[(code, int(seconds * FPS)) for code, seconds in plan])


def group_c():
    print("C. macroF1 vs spellF1 on a synthetic 4-minute stretch (10 possessions, 2 stoppages)")
    print("-" * 86)
    gt = pad_array(synthetic_half())
    alive = np.isin(gt, (H, A))
    rng = np.random.RandomState(0)

    def shift(codes, frames):
        out = codes.copy()
        out[frames:] = codes[:-frames]
        return out

    # ball "lost" in 25 random 1-3 s chunks during live play
    lost = np.zeros(len(gt), dtype=bool)
    for start in rng.choice(np.flatnonzero(alive), 25, replace=False):
        lost[start:start + rng.randint(25, 76)] = True
    lost &= alive

    # flicker: a 0.4 s flip to the other team every 3 s of live play
    flicker = gt.copy()
    for start in np.flatnonzero(alive)[::75]:
        stop = min(start + 10, len(gt))
        flicker[start:stop] = np.where(gt[start:stop] == H, A, np.where(gt[start:stop] == A, H, D))

    def fill_with(codes, mask, label):
        out = codes.copy()
        out[mask] = label
        return out

    merged = gt.copy()  # short possessions (2 s H, 3 s A) missed: absorbed by the team around them
    edges = np.flatnonzero(np.diff(np.concatenate(([-1], gt, [-1]))) != 0)
    for a, b in zip(edges[:-1], edges[1:]):
        if gt[a] in (H, A) and b - a <= 3 * FPS:
            merged[a:b] = gt[a - 1]

    cases = [
        ("C1 perfect", gt),
        ("C2 always D", np.full(len(gt), D, dtype=np.int8)),
        ("C3 always H", np.where(gt == D, H, H).astype(np.int8)),
        ("C4 perfect but everything 1 s late", shift(gt, 25)),
        ("C5 perfect but 0.4 s flicker every 3 s", flicker),
        ("C6 ball-lost chunks written as D", fill_with(gt, lost, D)),
        ("C7 ball-lost chunks written as X", fill_with(gt, lost, X)),
        ("C8 the 2 s and 3 s possessions missed", merged),
    ]
    runs = pm.valid_runs(gt)
    n_true = len(pm.possession_spells(gt, runs))
    print("{:<42} {:>8} {:>8} {:>13}".format("", "macroF1", "spellF1", "possessions"))
    for name, pred in cases:
        spells, macro = scores(gt, pred)
        n_pred = len(pm.possession_spells(pm.fill_abstentions(pred, runs), runs))
        print("{:<42} {:>8.3f} {:>8.3f} {:>6} / {:<5}".format(
            name, macro, spells["mean_f1"], n_pred, n_true))
    print()


if __name__ == "__main__":
    group_a()
    group_b()
    group_c()
