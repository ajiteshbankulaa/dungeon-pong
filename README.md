# Dungeon Pong: The Cathedral of Return

A story-driven skill game where Pong becomes a dungeon crawler. Fight through
25 current encounters, uncover the Cathedral's memories, draft sidegrade relics,
and master boss patterns without permanent stat inflation.

## Run

Requires Python 3.11+ and pygame 2.6.

```powershell
python -m pip install -r requirements.txt
python main.py
```

Controls: W/S or arrows move; Space uses Blink; E, Shift, or right-click uses
Chrono when equipped; Escape pauses. Xbox-style controllers use the left stick,
A for Blink, B for Chrono, and Menu to pause.

The Options menu includes Classic/Cathedral presentation, high contrast,
reduced flash, intensity, screen shake, UI scale, separate music/SFX levels,
and readability assists. Assists change preparation time, never damage.

## Campaign systems

- Five themed dungeon maps and 25 current combat encounters
- Authored story scenes, Codex memories, achievements, and permanent mastery
- Skill-neutral paddle cosmetics and elite relic drafts
- Deterministic daily challenge seeds
- Procedural SFX and an adaptive-score prototype loop
- Atomic, migrated save data in `data/save.json`

The complete 20–30 hour content plan and story are documented in
`NARRATIVE_BIBLE.md`; production priorities are in `PROFESSIONAL_INDIE_AUDIT.md`.

## Quality

```powershell
python -m pytest -q
python main.py --smoke
```

Smoke mode simulates and renders every encounter with temporary save data.

## License

See `LICENSE`. All current code and generated sound are repository-native;
future commissioned art/music must include explicit attribution and license
records before release.
