"""The moving objects. Float positions avoid frame-rate-dependent Rect truncation."""
from dataclasses import dataclass, field
import math
import pygame
from settings import (ARENA, PLAYER_H, PADDLE_W, BALL_RADIUS,
                      BALL_START_SPEED, BALL_MAX_SPEED, clamp)


@dataclass
class Paddle:
    x: float
    y: float
    height: float = PLAYER_H
    hp: int = 1
    target: float = ARENA.centery
    reaction: float = .2
    stun: float = 0

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y - self.height / 2), PADDLE_W, round(self.height))

    def move(self, amount, bounds):
        self.y = clamp(self.y + amount, bounds.top + self.height / 2, bounds.bottom - self.height / 2)


@dataclass
class Ball:
    x: float = ARENA.centerx
    y: float = ARENA.centery
    vx: float = BALL_START_SPEED
    vy: float = 90
    delay: float = .65
    charged: bool = False
    bank: bool = False
    slime: int = 0
    portal_cooldown: float = 0
    returned: bool = False
    phase_pending: bool = False
    hidden: float = 0.0
    hidden_total: float = 0.0
    trail: list = field(default_factory=list)
    # Phantom decoys created by the Wraith: the AI ignores them and they
    # dissolve on player-paddle contact or when they cross the goal line.
    decoy: bool = False
    decoy_life: float = 0.0   # seconds remaining before auto-dissolve
    fireball: bool = False    # INFERNO power: double damage, vaporizes projectiles, smashes obstacles
    fireball_timer: float = 0.0
    stasis_timer: float = 0.0 # Dream Eater & Nirvana stasis suspension
    stasis_vx: float = 0.0
    stasis_vy: float = 0.0
    yin_yang: int = 0         # Nirvana: 1 = Yin (Light/Cyan), -1 = Yang (Dark/Gold)
    relic_marked: bool = False
    relic_banked: bool = False

    def cap(self):
        # Gravity and repeated banks must not leave a near-vertical, endless rally.
        if abs(self.vx) < 220:
            self.vx = math.copysign(220, self.vx)
        self.vy = clamp(self.vy, -math.sqrt(BALL_MAX_SPEED ** 2 - 220 ** 2),
                        math.sqrt(BALL_MAX_SPEED ** 2 - 220 ** 2))
        speed = math.hypot(self.vx, self.vy)
        if speed > BALL_MAX_SPEED:
            self.vx *= BALL_MAX_SPEED / speed
            self.vy *= BALL_MAX_SPEED / speed

    def rebound(self, paddle, direction):
        offset = clamp((self.y - paddle.y) / (paddle.height / 2), -1, 1)
        speed = min(BALL_MAX_SPEED, math.hypot(self.vx, self.vy) * 1.025)
        angle = offset * math.radians(48)
        self.vx, self.vy = direction * speed * math.cos(angle), speed * math.sin(angle)
        self.x = paddle.x + PADDLE_W + BALL_RADIUS + .1 if direction > 0 else paddle.x - BALL_RADIUS - .1


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float = 0
    blockable: bool = False
    reflected: bool = False
    radius: int = 6
    soul_ember: bool = False   # Necromancer slow-homing ember; rendered in violet
    arrow: bool = False        # Standard skeleton/bone arrow (50% stun / 50% damage)
    hunter_bolt: bool = False  # Rapid sniper bolt (guaranteed damage unless 50% reflected)
    lightning: bool = False    # Zeus chain-lightning bolt
    blood_orb: bool = False    # Vampire King life-leech blood orb
    void_pulse: bool = False   # The Void gravitational pulse
    stone_rubble: bool = False # The Mason's flying stone rubble
    hellfire_skull: bool = False # Lord 666 demonic flaming skull
    holy_feather: bool = False # The Angel radiant holy dagger
    bubble: bool = False       # Leviathan deep sea tidal bubble


@dataclass
class Obstacle:
    rect: pygame.Rect
    hp: int = 1
    moving: bool = False
    warning: float = 0.0
    # acid_timer > 0: temporary slime puddle (dissolves when timer reaches 0)
    acid_timer: float = 0.0
    one_sided: bool = False    # Mason's wall: enemies shoot through, players bounce
    is_bone_spire: bool = False# Necromancer dynamic bone spire
    is_warp_rift: bool = False # Gatekeeper / cosmic warp rift
    is_tractor_beam: bool = False # The Alien mid-court saucer tractor beam
    is_whirlpool: bool = False # Leviathan ocean whirlpool vortex
    is_holy_beam: bool = False # The Angel vertical divine light pillar
    is_mandala: bool = False   # Nirvana celestial stasis mandala
    is_drone: bool = False     # The Alien orbiting defense drone



def circle_rect(x, y, radius, rect):
    near_x, near_y = clamp(x, rect.left, rect.right), clamp(y, rect.top, rect.bottom)
    return (x - near_x) ** 2 + (y - near_y) ** 2 <= radius ** 2
