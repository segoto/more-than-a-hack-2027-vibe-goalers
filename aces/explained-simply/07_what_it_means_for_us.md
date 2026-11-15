# 07 — What it means for us

Everything on the previous pages, turned into rules for building our system.

1. **Get the number of turns right.** Inventing turns (flicker) and missing turns (merging) are the
   two big ways to lose spellF1. Always look at how many turns our output has (the validator prints
   it). If it's far too many, something flickers.

2. **Never write `D` just because we can't see the ball.** The ball is invisible in 41% of the
   marked pictures. Writing `D` there cuts real turns into pieces (A4, C6). Keep the current team.

3. **Inside a turn, when unsure: don't change.** Keeping the same team is free (A5, C7). A wrong
   guess cuts the turn in pieces (A3).

4. **At a change of turn: commit to a time.** Don't let `X` or "same as before" drag the old team
   across the change (B7). Put the change at our best estimate.

5. **Short turns need precise edges.** With 1 second of error, turns under ~6 s start losing
   teachers, and turns under ~2 s are lost (B2, B3, the table on page 05). Long turns forgive.

6. **Pauses matter because they split turns.** Missing a pause between two turns of the same team
   (a throw-in back to the same side) merges two turns into one — very expensive (B5). Finding the
   real pauses is part of the possession problem.

7. **The edge where a turn meets another turn counts twice** (B1); the edge where a turn meets a
   pause counts once (B4). Precision is most valuable at turn-to-turn changes.

8. **Extra overlap never helps the neighbour.** Each turn dances once (B5, B6). Being "nearly
   right" across two turns is worth less than being right about one.

9. **Write the "same as before" ourselves instead of `X`.** It gives the same spellF1 and a better
   macroF1 (the tie-break) — and it lets us fill a gap with the *next* team when the gap sits just
   before a change, which `X` can't do.

10. **Never pick between versions using the 5 public minutes.** 17 turns is too few; the organisers'
    own example proves the public window picks the wrong version. All tuning happens on external
    matches.
