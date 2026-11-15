# 01 — The game we are playing

## A flip-book

A video is a **flip-book**: lots of pictures shown very fast. Our match video has **199,319
pictures**, 25 for every second.

For **every single picture** we must write one letter on a list:

```
picture 0      → X
picture 1      → X
...
picture 11185  → A      (Athletic has the ball)
picture 11186  → A
...
```

| letter | means | like… |
|---|---|---|
| `H` | Barcelona has the ball, game running | "it's the blue team's turn with the toy" |
| `A` | Athletic has the ball, game running | "it's the red team's turn with the toy" |
| `D` | the game is paused | "the toy is back in the box" |
| `X` | I don't know | "I'm not saying" |

Pictures before the match, at half-time and after the final whistle are **not marked** — we can
write anything there, nobody looks.

## Turns

Imagine two kids sharing a toy. A **turn** is a stretch of time where the same kid has it.

```
H H H H A A A H H H
└─turn─┘└turn┘└turn┘      = 3 turns
```

If the toy goes **back in the box** between two stretches, that is **two turns**, even if the same
kid gets it again:

```
H H H D D D H H H
└turn┘      └turn┘        = 2 turns (D is the pause, not a turn)
```

This rule is very important later.

## Who decides what is right?

The organisers have the correct list (the **truth**). They compare our list with theirs and give us
two scores:

- **macroF1** — "how many pictures did you get right?" (only used to break ties)
- **spellF1** — "how many **turns** did you find, as whole turns?" (this decides the ranking)

The next two pages explain each one.
