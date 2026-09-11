"""Small data table; unique phase changes stay in encounters.py."""
import json
from pathlib import Path

LEVELS = json.loads((Path(__file__).resolve().parent / "data" / "levels.json").read_text())
assert [level["level"] for level in LEVELS] == list(range(1, 26))
assert all((level["category"] == "BOSS") == (level["level"] % 5 == 0) for level in LEVELS)

POWER_CHOICES = {
    2: ("REFLECT", "SHOCK"),
    5: ("RICOCHET", "CHRONO"),
    10: ("AEGIS", "INFERNO"),
    15: ("TELEKINESIS", "CHRONO"),
    20: ("INFERNO", "AEGIS"),
}
POWER_TEXT = {
    "BLINK": "Space: emergency dash toward the true intercept. 3.6s cooldown.",
    "REFLECT": "50% chance to reflect enemy projectiles back from your paddle.",
    "SHOCK": "Every third return glows cyan and stuns for 1.4 seconds.",
    "RICOCHET": "Wall banks charge shots, smash cover, and amplify charged scores.",
    "CHRONO": "E / Shift: warp time to 35% speed for 2.5s. 7s cooldown.",
    "AEGIS": "Passive: radiant barrier absorbs 1 fatal miss every 18 seconds.",
    "INFERNO": "Striking after 2 wall banks ignites an explosive fireball (2x damage).",
    "TELEKINESIS": "Hold W/S in flight to psionically curve the ball's trajectory.",
}
