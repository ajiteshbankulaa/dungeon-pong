"""Procedural retro SFX synthesized in memory. No wav/mp3 assets required.

Sounds are generated once on startup and cached. Every public method is safe to
call even when the mixer is unavailable (headless, test environment, or user
toggled audio off) – it simply returns immediately.
"""
import math
import struct
import array as _array

# Guard against environments where pygame.mixer cannot open a device.
try:
    import pygame
    _HAVE_PYGAME = True
except ImportError:  # pragma: no cover
    _HAVE_PYGAME = False

_RATE = 22050   # Hz
_CHANNELS = 1   # mono
_SIZE = -16     # signed 16-bit


def _buf(frames):
    """Return a zeroed signed-16 array of *frames* samples."""
    return _array.array("h", bytes(frames * 2))


def _to_sound(arr):
    """Wrap a signed-16 array as a pygame Sound, or return None."""
    if not _HAVE_PYGAME:
        return None
    try:
        snd = pygame.sndarray.make_sound(arr)
        return snd
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  Waveform generators                                                         #
# --------------------------------------------------------------------------- #

def _sine(freq, duration, volume=0.5, envelope=(0.01, 0.0, 1.0, 0.05)):
    """Pure sine tone with ADSR-lite envelope (attack, decay, sustain, release)."""
    n = int(_RATE * duration)
    buf = _buf(n)
    attack_s, decay_s, sustain_level, release_s = envelope
    attack = int(attack_s * _RATE)
    decay = int(decay_s * _RATE)
    release = int(release_s * _RATE)
    sustain_start = attack + decay
    release_start = max(sustain_start, n - release)
    peak = 32767 * volume
    for i in range(n):
        t = i / _RATE
        amp = (peak * i / attack) if i < attack else \
              (peak * (1 - (1 - sustain_level) * (i - attack) / max(1, decay))) if i < sustain_start else \
              (peak * sustain_level) if i < release_start else \
              (peak * sustain_level * (1 - (i - release_start) / max(1, release)))
        buf[i] = int(amp * math.sin(2 * math.pi * freq * t))
    return buf


def _square(freq, duration, volume=0.4, duty=0.5):
    """Square wave with simple fade-out."""
    n = int(_RATE * duration)
    buf = _buf(n)
    period = _RATE / max(1, freq)
    for i in range(n):
        phase = (i % period) / period
        amp = 32767 * volume * (1 - i / n)
        buf[i] = int(amp * (1 if phase < duty else -1))
    return buf


def _noise(duration, volume=0.3, cutoff=0.98):
    """White noise with exponential decay (useful for impacts, crackle)."""
    import random
    rng = random.Random(42)
    n = int(_RATE * duration)
    buf = _buf(n)
    filt = 0.0
    for i in range(n):
        sample = rng.uniform(-1, 1)
        filt = filt * cutoff + sample * (1 - cutoff)
        decay = (1 - i / n) ** 2
        buf[i] = int(filt * 32767 * volume * decay)
    return buf


def _sweep(freq_start, freq_end, duration, volume=0.45, wave="sine"):
    """Frequency sweep (pitch slide) over *duration* seconds."""
    n = int(_RATE * duration)
    buf = _buf(n)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        decay = (1 - t) ** 1.4
        sample = math.sin(phase) if wave == "sine" else (1 if math.sin(phase) >= 0 else -1)
        buf[i] = int(sample * 32767 * volume * decay)
        phase += 2 * math.pi * freq / _RATE
    return buf


def _mix(*buffers):
    """Sum multiple same-length arrays, clamping to int16 range."""
    n = min(len(b) for b in buffers)
    out = _buf(n)
    for i in range(n):
        val = sum(b[i] for b in buffers)
        out[i] = max(-32767, min(32767, val))
    return out


def _pad(buf, target_n):
    """Right-pad with silence to *target_n* samples."""
    if len(buf) >= target_n:
        return buf
    result = _buf(target_n)
    for i, v in enumerate(buf):
        result[i] = v
    return result


# --------------------------------------------------------------------------- #
#  Sound recipes                                                                #
# --------------------------------------------------------------------------- #

def _make_paddle_hit():
    """Crisp click – a very short sine chirp."""
    return _mix(
        _pad(_sine(520, 0.045, volume=0.55, envelope=(0.002, 0.0, 1.0, 0.04)), int(_RATE * 0.07)),
        _pad(_sine(780, 0.025, volume=0.25, envelope=(0.002, 0.0, 1.0, 0.02)), int(_RATE * 0.07)),
    )


def _make_wall_bounce():
    """Woody blip – lower pitched than paddle."""
    return _sine(310, 0.055, volume=0.45, envelope=(0.002, 0.0, 1.0, 0.05))


def _make_damage():
    """Low crunchy buzz + noise burst."""
    n = int(_RATE * 0.28)
    sq = _pad(_square(80, 0.18, volume=0.5, duty=0.6), n)
    ns = _pad(_noise(0.25, volume=0.4, cutoff=0.85), n)
    return _mix(sq, ns)


def _make_bone_spawn():
    """Crackling stone rumble."""
    n = int(_RATE * 0.22)
    lo = _pad(_noise(0.20, volume=0.5, cutoff=0.92), n)
    tone = _pad(_sweep(180, 90, 0.18, volume=0.3, wave="square"), n)
    return _mix(lo, tone)


def _make_bone_break():
    """Sharp crack + gravel scatter."""
    n = int(_RATE * 0.18)
    ns = _pad(_noise(0.18, volume=0.6, cutoff=0.75), n)
    sweep = _pad(_sweep(300, 80, 0.15, volume=0.35, wave="square"), n)
    return _mix(ns, sweep)


def _make_phantom_phase():
    """Ethereal dual-frequency shimmer."""
    n = int(_RATE * 0.55)
    a = _pad(_sweep(660, 1320, 0.5, volume=0.35), n)
    b = _pad(_sweep(880, 440, 0.5, volume=0.25), n)
    return _mix(a, b)


def _make_soul_ember():
    """Soft whirring hiss – slow homing projectile."""
    n = int(_RATE * 0.35)
    a = _pad(_sweep(440, 550, 0.3, volume=0.3), n)
    ns = _pad(_noise(0.3, volume=0.15, cutoff=0.96), n)
    return _mix(a, ns)


def _make_shock_stun():
    """Electric cyan buzz."""
    n = int(_RATE * 0.30)
    sq = _pad(_square(220, 0.28, volume=0.45, duty=0.3), n)
    hi = _pad(_sweep(1200, 800, 0.25, volume=0.2), n)
    return _mix(sq, hi)


def _make_laser_fire():
    """Pitch slide down – red projectile launch."""
    return _sweep(900, 200, 0.18, volume=0.4, wave="square")


def _make_blink_dash():
    """High-to-low whoosh with a landing thud."""
    n = int(_RATE * 0.22)
    whoosh = _pad(_sweep(1100, 350, 0.18, volume=0.4), n)
    thud = _pad(_sine(140, 0.08, volume=0.3, envelope=(0.002, 0.0, 1.0, 0.07)), n)
    return _mix(whoosh, thud)


def _make_menu_click():
    """Soft UI click."""
    return _sine(660, 0.04, volume=0.35, envelope=(0.001, 0.0, 1.0, 0.035))


def _make_enemy_hurt():
    """Enemy takes damage – bright sting."""
    return _sweep(1000, 500, 0.14, volume=0.4)


def _make_victory():
    """Short ascending fanfare."""
    n = int(_RATE * 0.7)
    parts = []
    for i, freq in enumerate((440, 550, 660, 880)):
        start = int(i * 0.15 * _RATE)
        tone = _sine(freq, 0.25, volume=0.4, envelope=(0.01, 0.0, 1.0, 0.1))
        padded = _buf(n)
        for j, v in enumerate(tone):
            if start + j < n:
                padded[start + j] = v
        parts.append(padded)
    return _mix(*parts)


def _make_acid_splat():
    """Wet bubbling – slime puddle lands."""
    n = int(_RATE * 0.20)
    ns = _pad(_noise(0.18, volume=0.4, cutoff=0.93), n)
    lo = _pad(_sweep(200, 120, 0.18, volume=0.3), n)
    return _mix(ns, lo)


def _make_cathedral_loop():
    """Eight-second restrained arpeggio; a replaceable adaptive-score prototype."""
    n = int(_RATE * 8.0)
    layers = []
    for beat, freq in enumerate((110, 165, 220, 247, 110, 196, 220, 330,
                                  110, 165, 262, 247, 110, 196, 294, 220)):
        start = int(beat * .5 * _RATE)
        tone = _sine(freq, .7, volume=.075, envelope=(.08, .05, .65, .25))
        padded = _buf(n)
        for i, sample in enumerate(tone):
            if start + i < n:
                padded[start + i] = sample
        layers.append(padded)
    return _mix(*layers)


# --------------------------------------------------------------------------- #
#  Public Audio class                                                           #
# --------------------------------------------------------------------------- #

class Audio:
    """Singleton-style audio manager.  Call ``Audio()`` once in main, then pass
    it around.  All play methods are no-ops if sound is disabled or unavailable.
    """

    def __init__(self, enabled=True):
        self._ok = False
        self._sounds: dict = {}
        self.enabled = enabled
        self.sfx_volume = 1.0
        if not _HAVE_PYGAME:
            return
        try:
            pygame.mixer.init(frequency=_RATE, size=_SIZE, channels=_CHANNELS, buffer=512)
            self._ok = True
        except pygame.error:
            return
        recipes = {
            "paddle":      _make_paddle_hit,
            "wall":        _make_wall_bounce,
            "damage":      _make_damage,
            "bone_spawn":  _make_bone_spawn,
            "bone_break":  _make_bone_break,
            "phantom":     _make_phantom_phase,
            "soul_ember":  _make_soul_ember,
            "shock":       _make_shock_stun,
            "laser":       _make_laser_fire,
            "blink":       _make_blink_dash,
            "menu":        _make_menu_click,
            "enemy_hurt":  _make_enemy_hurt,
            "victory":     _make_victory,
            "acid":        _make_acid_splat,
            "music":       _make_cathedral_loop,
        }
        for name, fn in recipes.items():
            try:
                snd = _to_sound(fn())
                if snd is not None:
                    self._sounds[name] = snd
            except Exception:
                pass  # degrade gracefully

    # ---------------------------------------------------------------------- #

    def play(self, name: str, volume: float = 1.0):
        if not self._ok or not self.enabled:
            return
        snd = self._sounds.get(name)
        if snd is None:
            return
        snd.set_volume(max(0.0, min(1.0, volume * self.sfx_volume)))
        snd.play()

    # Convenience wrappers (callers don't need to remember string keys)

    def paddle_hit(self):    self.play("paddle")
    def wall_bounce(self):   self.play("wall")
    def player_hurt(self):   self.play("damage")
    def enemy_hurt(self):    self.play("enemy_hurt")
    def bone_spawn(self):    self.play("bone_spawn")
    def bone_break(self):    self.play("bone_break")
    def phantom_phase(self): self.play("phantom")
    def soul_ember(self):    self.play("soul_ember")
    def shock_stun(self):    self.play("shock")
    def laser_fire(self):    self.play("laser")
    def blink_dash(self):    self.play("blink")
    def menu_click(self):    self.play("menu")
    def victory(self):       self.play("victory")
    def acid_splat(self):    self.play("acid")

    def start_music(self, volume=.24):
        if not self._ok or not self.enabled or "music" not in self._sounds:
            return
        self._sounds["music"].set_volume(max(0.0, min(1.0, volume)))
        self._sounds["music"].play(loops=-1, fade_ms=700)

    def set_music_volume(self, volume):
        if "music" in self._sounds:
            self._sounds["music"].set_volume(max(0.0, min(1.0, volume)))

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not self._ok:
            return
        if enabled:
            self.start_music()
        else:
            pygame.mixer.stop()
