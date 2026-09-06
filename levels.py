"""Small data table; unique phase changes stay in encounters.py."""
import json
from pathlib import Path

LEVELS = json.loads((Path(__file__).resolve().parent / "data" / "levels.json").read_text())
assert [level["level"] for level in LEVELS] == list(range(1, 21))
assert all((level["category"] == "BOSS") == (level["level"] % 5 == 0) for level in LEVELS)

POWER_CHOICES = {
    2: ("BLINK", "REFLECT"),
    5: ("SHOCK", "RICOCHET"),
    10: ("BLINK", "REFLECT"),
    15: ("SHOCK", "RICOCHET"),
}
POWER_TEXT = {
    "BLINK": "Space: dash up to 210px toward an incoming ball. 2.8s cooldown.",
    "REFLECT": "Every enemy projectile bounces back from your paddle.",
    "SHOCK": "Every third return glows cyan and stuns for 1.4 seconds.",
    "RICOCHET": "Wall banks charge shots, smash cover, and amplify charged scores.",
}
