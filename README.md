# Dungeon Pong

**It's Pong, but a dungeon crawler.** Twenty short encounters gradually turn a
familiar duel into portals, multiball, survival, destructible cover, and bosses.
Black, white, a few warning colors. Three HP. No inventory or currencies.

## Play

Requires Python 3.10+ and pygame:

```sh
python -m pip install -r requirements.txt
python main.py
```

`python pong.py` also works. Move with **W/S or Up/Down**, use **Space** for Blink,
and **Esc** to pause. Menus support arrows, Enter/Space, and mouse clicks. Losing
window focus pauses automatically. Paddle-tip returns create sharper angles.

### Read the arena

- **Solid white circle:** return it. Missing costs one HP. A Wraith can briefly phase it out after a purple midcourt tell.
- **Filled red diamond + streak:** dodge it. Passing your goal is harmless.
- **Outlined gold diamond:** block it with your paddle or dodge it. Reflect sends it back.
- **Cyan:** your charged ball or reflected shot.
- **Purple outlines:** harmless phantom copies, portal edges, or a teleport tell.
- **Crossed white rectangles:** destructible cover. Plain outlined wall: bank around it.
- **Dashed horizontal lines:** upcoming projectile lanes; launch follows after 0.85 seconds.

Red shots fizzle in the immediate return corridor of an incoming white ball to
avoid demanding conflicting actions. Waves leave a channel larger than the paddle.
Hits grant 1.25 seconds of recovery. Gold shots are always blockable without a
power. Blink grants a brief safe dash.

### Progress and powers

HP restores each level. Boss victories at **5, 10, 15, 20** unlock checkpoints.
Continue loads the next level after your last clear, with your selected powers.
After death, Continue and Restart use the latest defeated boss checkpoint (the
following level). No active rally is saved. Play begins a fresh run while keeping
lifetime unlocks and statistics. Clearing level 20 leaves the final boss replayable.

At four milestones, choose from at most two powers:

| Power | Effect |
| --- | --- |
| Blink | Space dashes up to 210px toward an incoming ball; 2.8-second cooldown and a brief safe window. |
| Reflect | Every hostile projectile reflects, stunning enemies, breaking cover, or striking an open core. |
| Shock | Every third return charges cyan; enemy contact stuns for 1.4 seconds. |
| Ricochet | Wall banks charge and accelerate shots, smash cover, and amplify a Shock score. |

Bosses unlock cosmetic paddle styles in Options. Effects and high contrast can be
toggled independently. All encounters can be played without any power.
Blink is the only active power and uses Space. Reflect, Shock, and Ricochet are
automatic passives; the HUD shows their charge or status, and short callouts mark
every activation.

### Encounters

1–4 teach returns, guard, phantom copies, and breakable walls. The Bone King (5)
adds blockable attacks and cover. Levels 6–9 introduce moving walls, a hunter,
two balls, and portals. The Phantom Queen (10) adds echoes, gates, and teleports.
11–14 add sparse waves, gravity, individually destructible paddles, and survival.
The Bullet Saint (15) replaces the paddle with an intermittently open core.
16–19 shrink the arena, protect a Breakout vault, combine two balls with portals,
and put you on the right. The Architect (20) goes from duel to multiball, core
combat, collapsing walls, and finally a single decisive rally.
In the last rally, one returned ball touching the enemy wins; one missed ball loses.

## Small code map

`main.py` initializes pygame; `game.py` owns simulation and lifecycle;
`entities.py` holds four object types and a collision helper;
`encounters.py` composes arena/pattern rules and boss phases;
`levels.py` loads `data/levels.json`; `save.py` validates and atomically writes
progress; `ui.py` renders; `settings.py` holds shared geometry and colors.

The fixed 120 Hz simulation uses floating-point positions and capped velocities.
Balls, enemies, projectiles, and obstacles are lists. Configurations override
ball count, arena, objective, gravity, and player side. Unique bosses use a small
explicit phase script instead of a generic framework.

Saves live beside the game at `data/save.json` (ignored by Git). Missing fields
receive defaults, malformed files are preserved as `save.json.corrupt`, and an
unwritable directory displays a warning while play continues in memory.

## Validation

```sh
python -m unittest discover -s tests -v
python main.py --smoke --screenshots artifacts
```

Tests and smoke renders use temporary saves. See [AUDIT.md](AUDIT.md) for the
baseline findings and [TESTING.md](TESTING.md) for verification details and limits.
Encounter targets are 30–120 seconds, with bosses roughly 2–4 minutes; actual
times depend on skill and need human playtesting.

## Attribution

Based on / inspired by Ericson Willians' [PyClassicPong](https://github.com/EricsonWillians/PyClassicPong),
GPL-3.0. This project retains that attribution and is distributed under GPL-3.0;
see [LICENSE](LICENSE). The exact original single-file playtest is preserved in
Git as tag `original-playtest` (commit `3eeeafb`).
