"""Small data table; unique phase changes stay in encounters.py."""
import json
from pathlib import Path

ARCHETYPES = json.loads((Path(__file__).resolve().parent / "data" / "levels.json").read_text())

ROOM_NAMES = (
    ("MOSS AT THE TURNSTILE", "COIN-GHOST", "SILT CHILD", "CABINET OSSUARY", "THE BONE CASHIER",
     "FLOODED WORKSHOP", "PRIZE-COUNTER HUNTER", "THE TOKEN TWINS", "RUSTED GATE", "QUEEN OF LOST QUARTERS",
     "DROWNED CHORUS", "NAP ROOM", "CRANE-GAME SWARM", "BLACKOUT AISLE", "SAINT OF THE HIGH SCORE",
     "NEON STORM", "THE LOCKED CABINET", "TWIN TURNSTILES", "PLAYER TWO", "THE RED MARQUEE",
     "EXIT-LIGHT ANGEL", "LEVIATHAN IN THE CARPET", "QUIET JACKPOT", "SKYLIGHT MACHINE", "THE BONE KING"),
    ("FIRST FOOTPRINT", "VELVET SKELETON", "PORTRAIT WRAITH", "TROPHY KEEPER", "THE MASON OF TRACKS",
     "MOVING GALLERY", "JUNE, THE HUNTER", "SISTER TARGETS", "GALLERY WARDEN", "ADA IN THE GLASS",
     "CHOIR OF ARROWS", "SLEEPING EXHIBIT", "THE UNCHOSEN SWARM", "EMPTY FRAME", "SAINT OF AIM",
     "THUNDER PORTRAIT", "THE TROPHY VAULT", "TWIN SIGHTLINES", "MIRROR PLAYER", "THE ANGRY CURATOR",
     "MERCY'S WING", "HUNT BELOW", "THE OPEN HAND", "CONSTELLATION HALL", "THE PHANTOM QUEEN"),
    ("LOW NOTE", "MARROW METRONOME", "LULLABY WRAITH", "MEMORY SURGEON", "CONDUCTOR OF BONES",
     "ENGINE MASON", "THE LISTENING GUN", "COUNTERPOINT TWINS", "DREAM GATE", "QUEEN OF STATIC",
     "THE CHORISTER", "DREAM EATER", "SLEEPWALKING HOST", "THE MISSING MEASURE", "BULLET SAINT",
     "ELECTRIC LULLABY", "ARCHIVE VAULT", "TWIN PULSES", "BORROWED REFLECTION", "THE FURNACE BELOW",
     "ANGEL OF SILENCE", "LEVIATHAN'S DREAM", "NIRVANA ERROR", "THE MEMORY ENGINE", "THE EMPTY NOTE"),
    ("ASH PILGRIM", "HALO SKELETON", "WRAITH OF WRATH", "RELIQUARY KEEPER", "THE THUNDER KING",
     "MASON OF HEAVEN", "HERESY HUNTER", "TWIN JUDGES", "PEARL GATE", "QUEEN OF BLAME",
     "WAR CHORISTER", "THE GUILT DREAM", "SERAPH SWARM", "GODLESS VOID", "SAINT UNMADE",
     "ZEUS", "THE MERCY VAULT", "TWIN TESTAMENTS", "THE ACCUSED", "LORD 666",
     "THE ANGEL", "LEVIATHAN ASCENDING", "NIRVANA WAR", "BROKEN FIRMAMENT", "THE THIRD DOOR"),
    ("RETURN ONE", "PERFECT SKELETON", "REPLAY WRAITH", "LOOP MASON", "THE FIRST COPY",
     "MOVING MEMORY", "HUNTER REMEMBERED", "TWIN SELVES", "LAST GATEKEEPER", "MARA'S SHADOW",
     "FINAL CHORUS", "ILYAN DREAMING", "EVERY LOST FUTURE", "THE PAUSE BETWEEN", "SAINT OF TOMORROW",
     "STORM AT THE WINDOW", "THE LOCKED MORNING", "TWIN HEARTS", "THE ORIGINAL", "GRIEF WITHOUT A DEVIL",
     "MARA'S RETURN", "LEVIATHAN RELEASED", "JOY WITHOUT PERMISSION", "THE OPEN SKY", "THE ARCHITECT"),
)


def _build_campaign():
    levels = []
    for dungeon, names in enumerate(ROOM_NAMES):
        for room, (name, source) in enumerate(zip(names, ARCHETYPES), 1):
            item = dict(source)
            item.update(level=dungeon * 25 + room, dungeon=dungeon + 1, room=room,
                        template_level=source["level"], template_name=source["name"], name=name)
            item["speed"] = min(285, item.get("speed", 240) + dungeon * 4)
            item["error"] = max(90, item.get("error", 130) - dungeon * 3)
            item["hint"] = f"{item['hint']}  Memory {dungeon + 1}.{room:02d}."
            levels.append(item)
    return levels


LEVELS = _build_campaign()
assert [level["level"] for level in LEVELS] == list(range(1, 126))
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
