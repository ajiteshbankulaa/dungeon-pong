"""Versioned progress only. Never serialize a rally or a pygame object."""
import copy
import json
import math
import os
from pathlib import Path

POWERS = ("BLINK", "REFLECT", "SHOCK", "RICOCHET", "CHRONO", "AEGIS", "INFERNO", "TELEKINESIS")
COSMETICS = ("SOLID", "OUTLINE", "NOTCHED")
MAX_LEVELS = 25
DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "save.json"
DEFAULT = {
    "version": 1, "highest_level": 1, "checkpoint": 0, "continue_level": 1,
    "completed": False, "pending_power_level": 0, "unlocked_powers": [], "equipped_powers": [],
    "checkpoint_powers": [], "unlocked_cosmetics": ["SOLID"],
    "selected_cosmetic": "SOLID", "settings": {"effects": True, "high_contrast": False, "sound": True},
    "stats": {key: 0 for key in (
        "wins", "losses", "returns", "damage_taken", "bosses_defeated",
        "enemies_defeated", "deaths", "longest_rally", "projectiles_dodged",
        "projectiles_reflected", "abilities_used", "perfect_levels", "run_time")},
}


class SaveStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_PATH
        self.error = None
        self.data = copy.deepcopy(DEFAULT)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Save must be an object")
            self._merge(raw)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            # Keep the original bytes available when possible, then recover defaults.
            try:
                self.path.replace(self.path.with_suffix(".json.corrupt"))
            except OSError:
                pass
        self.flush()

    def _merge(self, raw):
        for key, lo, hi in (("highest_level", 1, MAX_LEVELS), ("continue_level", 1, MAX_LEVELS), ("checkpoint", 0, MAX_LEVELS)):
            value = raw.get(key, self.data[key])
            if type(value) is int:
                self.data[key] = max(lo, min(hi, value))
        self.data["checkpoint"] = self.data["checkpoint"] // 5 * 5
        self.data["checkpoint"] = min(self.data["checkpoint"], self.data["highest_level"] // 5 * 5)
        self.data["continue_level"] = min(self.data["continue_level"], self.data["highest_level"])
        if "continue_level" not in raw:
            self.data["continue_level"] = min(MAX_LEVELS, self.data["checkpoint"] + 1)
        self.data["completed"] = raw.get("completed") is True
        pending = raw.get("pending_power_level", 0)
        if type(pending) is int and pending in (2, 5, 10, 15, 20) and self.data["continue_level"] == pending + 1:
            self.data["pending_power_level"] = pending
        for key, allowed in (("unlocked_powers", POWERS), ("equipped_powers", POWERS),
                             ("checkpoint_powers", POWERS), ("unlocked_cosmetics", COSMETICS)):
            values = raw.get(key, [])
            if isinstance(values, list):
                self.data[key] = [v for v in allowed if v in values]
        if "SOLID" not in self.data["unlocked_cosmetics"]:
            self.data["unlocked_cosmetics"].insert(0, "SOLID")
        selected = raw.get("selected_cosmetic")
        if selected in self.data["unlocked_cosmetics"]:
            self.data["selected_cosmetic"] = selected
        settings = raw.get("settings", {})
        if isinstance(settings, dict):
            for key in self.data["settings"]:
                if type(settings.get(key)) is bool:
                    self.data["settings"][key] = settings[key]

        stats = raw.get("stats", {})
        if isinstance(stats, dict):
            for key in self.data["stats"]:
                value = stats.get(key, 0)
                if type(value) is int:
                    self.data["stats"][key] = max(0, min(10**12, value))
                elif type(value) is float and math.isfinite(value):
                    self.data["stats"][key] = max(0, min(10**12, value))

    def flush(self):
        temporary = self.path.with_suffix(".json.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(self.data, stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            self.error = None
            return True
        except (OSError, ValueError) as exc:
            self.error = f"Progress could not be saved: {exc}"
            return False
