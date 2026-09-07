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


@dataclass
class Obstacle:
    rect: pygame.Rect
    hp: int = 1
    moving: bool = False
    warning: float = .8


def circle_rect(x, y, radius, rect):
    near_x, near_y = clamp(x, rect.left, rect.right), clamp(y, rect.top, rect.bottom)
    return (x - near_x) ** 2 + (y - near_y) ** 2 <= radius ** 2
