"""Small data table; unique phase changes stay in encounters.py."""
import json
from pathlib import Path

LEVELS = json.loads((Path(__file__).resolve().parent / "data" / "levels.json").read_text())
assert [level["level"] for level in LEVELS] == list(range(1, 21))
assert all((level["category"] == "BOSS") == (level["level"] % 5 == 0) for level in LEVELS)

POWER_CHOICES = {
    2: ("REFLECT", "SHOCK"),
    5: ("RICOCHET", "REFLECT"),
    10: ("SHOCK", "RICOCHET"),
    15: ("REFLECT", "SHOCK"),
}
POWER_TEXT = {
    "BLINK": "Space: emergency dash toward the true intercept. 3.6s cooldown.",
    "REFLECT": "Every enemy projectile bounces back from your paddle.",
    "SHOCK": "Every third return glows cyan and stuns for 1.4 seconds.",
    "RICOCHET": "Wall banks charge shots, smash cover, and amplify charged scores.",
}
