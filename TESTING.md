# Testing Dungeon Pong

Run `python -m pytest -q` for simulation, persistence, campaign, render, and
secondary prototype coverage. Run `python main.py --smoke` for a headless pass
through all encounters. CI runs both commands on Windows and Linux.

Before a tagged build, manually verify keyboard and controller navigation,
Classic and Cathedral presentation, reduced-flash and high-contrast modes,
sound-off startup, a new save, a migrated older save, checkpoint recovery,
story advancement, relic selection, Codex unlocks, and daily challenge launch.

Fairness playtests should record room, death cause, perceived fairness,
telegraph recognition, retry count, and chosen assist. No encounter ships if
simultaneous hazards require an impossible save.
