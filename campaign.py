"""Authored campaign metadata. Combat mechanics remain in levels/encounters."""
from datetime import date
import hashlib

DUNGEONS = (
    {"name": "THE SILT ARCADE", "levels": range(1, 6), "color": (74, 214, 152),
     "motif": "What survives when a place forgets its players?"},
    {"name": "THE HUNT GALLERY", "levels": range(6, 11), "color": (210, 90, 255),
     "motif": "Can an enemy choose to become an ally?"},
    {"name": "THE DREAM ENGINE", "levels": range(11, 16), "color": (92, 148, 255),
     "motif": "Every restored memory costs another."},
    {"name": "THE BROKEN HEAVENS", "levels": range(16, 21), "color": (255, 196, 74),
     "motif": "Who deserves the memories of a dying world?"},
    {"name": "THE INFINITE COURT", "levels": range(21, 26), "color": (255, 90, 110),
     "motif": "A perfect loop can never grow."},
)

STORY = {
    1: ("SLIME", "Keeper? I waited so long the floor learned my name.",
        "THE KEEPER", "I woke with no name at all.",
        "SLIME", "Then borrow mine. I am Moss. I used to laugh when the lights went out.",
        "MOSS", "The Cathedral is returning rooms, but everyone inside them is fading.",
        "THE KEEPER", "What does it want from me?",
        "MOSS", "Only what games ever want: send something away, and pray it comes back."),
    5: ("BONE KING", "Every return restores this place—and buries what came before.",
        "THE KEEPER", "You built your throne from those remains.",
        "BONE KING", "No. I built a memorial. The Architect calls memorials corrupted data.",
        "MOSS", "Keeper... the names on those bones are appearing on your paddle.",
        "BONE KING", "Win if you must. But remember that a clean save can still be a grave.",
        "THE KEEPER", "Then I will carry every name the Cathedral tries to clean."),
    6: ("THE HUNTER", "The Architect calls you a fault in the pattern.",
        "THE KEEPER", "Patterns can change.",
        "THE HUNTER", "That sentence got my whole Gallery erased once.",
        "MOSS", "You remember an erasure?",
        "THE HUNTER", "I remember a girl at a hospital window, teaching her brother to aim.",
        "THE KEEPER", "Why does that feel like my memory?"),
    10: ("PHANTOM QUEEN", "My ghosts are not copies. They are choices the loop refused to keep.",
         "THE KEEPER", "The cowardice, the anger, the lives we nearly lived.",
         "PHANTOM QUEEN", "Free me, and the Gallery will hunt its maker.",
         "THE HUNTER", "My Queen, I hunted you for nine thousand returns.",
         "PHANTOM QUEEN", "Then spend the next nine thousand walking beside me.",
         "THE KEEPER", "Stand with us. Keep your names."),
    11: ("CHORISTER", "Listen. The song loses a note whenever you win.",
         "MOSS", "I thought the silence meant we were getting closer.",
         "CHORISTER", "The machine has a fixed amount of memory. Restoration is replacement.",
         "THE KEEPER", "Then the things I defeated...",
         "CHORISTER", "Were not monsters. They were originals refusing to be overwritten.",
         "THE KEEPER", "I hear the missing voices now. I will not call them noise again."),
    15: ("BULLET SAINT", "You want absolution because you did not know. The erased remain erased.",
         "THE KEEPER", "Tell me how to stop the Engine.",
         "BULLET SAINT", "It is fed by grief. Yours is an ocean.",
         "MOSS", "Keeper, your reflection—there is a hospital bracelet around its wrist.",
         "BULLET SAINT", "Mercy is not refusing the shot. It is choosing what the shot protects.",
         "THE KEEPER", "Open the way. I will learn whose grief built this place."),
    16: ("ZEUS", "Memory belongs to whoever can hold the lightning.",
         "THE KEEPER", "Memory belongs to the remembered.",
         "ZEUS", "Pretty. False. The child died. His sister could not permit the world to continue.",
         "MOSS", "What child?",
         "ZEUS", "Ilyan. He made a paddle from a ruler. Mara always let him serve first.",
         "THE KEEPER", "I remember being both of them."),
    20: ("LORD 666", "Heaven and hell are teams Mara invented to make guilt look orderly.",
         "THE ANGEL", "And you made cruelty look honest.",
         "LORD 666", "At least I admit that anger kept the dead warm.",
         "THE KEEPER", "I am Mara's copy, built from the night Ilyan died.",
         "MOSS", "You are also every choice you made after waking.",
         "THE KEEPER", "Then the next match has no teams. We go together."),
    21: ("THE ANGEL", "Beyond this gate, even victory becomes a cage.",
         "THE KEEPER", "The Architect is the original Mara.",
         "THE ANGEL", "No. That is the kinder lie. You are the original.",
         "MOSS", "Keeper?",
         "THE ANGEL", "The Architect is Ilyan—the brother who survived. Mara died that night.",
         "THE KEEPER", "A door is still a door. Even when I fear what waits behind it."),
    25: ("THE ARCHITECT", "I made the perfect game: no ending, no loss, no change.",
         "THE KEEPER", "You made me believe I was you.",
         "THE ARCHITECT", "Because I could not bear to remember that Mara saved me and died.",
         "MOSS", "We were never her memories. We were yours—wearing costumes from your game.",
         "THE ARCHITECT", "If the loop ends, she is gone.",
         "THE KEEPER", "No. If it ends, she becomes a whole life instead of one terrible night.",
         "THE ARCHITECT", "What comes after the final point?",
         "THE KEEPER", "Breakfast. Sunlight. Missing her. Loving people anyway.",
         "MARA", "Then serve, little brother.",
         "ILYAN", "Only if you promise to return.",
         "MARA", "I already did."),
}

RELICS = {
    "BANKED OATH": "A wall bank charges the next paddle return with a brighter impact.",
    "MERCY GLASS": "Perfect levels reveal an additional memory in the Codex.",
    "ECHO THREAD": "Long rallies leave a visible trajectory echo; physics are unchanged.",
    "QUIET BELL": "Enemy telegraphs gain a distinct shape in high-intensity encounters.",
    "HUNTER'S MARK": "Center-paddle returns mark the ball gold until its next collision.",
}

CODEX = (
    ("THE KEEPER", "A title passed between players. The paddle is a key, not a weapon."),
    ("THE SILT ARCADE", "The first court sank while its cabinets kept waiting for coins."),
    ("THE ARCHITECT", "It feared loss so deeply that it mistook repetition for life."),
    ("THE RETURN", "The instant a ball changes direction—and the smallest possible act of hope."),
    ("THE MISSING NOTE", "A memory sacrificed to keep the Cathedral's loop seamless."),
)

ACHIEVEMENTS = {
    "FIRST RETURN": "Return your first ball.",
    "UNTOUCHABLE": "Clear an encounter without taking damage.",
    "BONE BROKEN": "Defeat the first dungeon boss.",
    "KEEPER": "Reach the Infinite Court.",
    "CHANGE THE LOOP": "Defeat the Architect.",
}


def dungeon_for(level):
    return DUNGEONS[min(4, max(0, (level - 1) // 5))]


def daily_seed(today=None):
    stamp = (today or date.today()).isoformat().encode("ascii")
    return int.from_bytes(hashlib.sha256(b"DungeonPong:" + stamp).digest()[:4], "big")


def map_nodes(highest_level):
    """Five compact themed routes; locked nodes remain visible."""
    nodes = []
    for level in range(1, 26):
        dungeon = dungeon_for(level)
        branch = (-1, 0, 1, 0, 0)[(level - 1) % 5]
        nodes.append({"level": level, "name": dungeon["name"], "branch": branch,
                      "boss": level % 5 == 0, "unlocked": level <= highest_level})
    return nodes
