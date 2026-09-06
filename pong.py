"""
DUNGEON PONG
"It's Pong, but a dungeon crawler."

Single-file classroom playtest build.
Requires only pygame.

Based on / inspired by Ericson Willians' PyClassicPong (GPL-3.0):
https://github.com/EricsonWillians/PyClassicPong

Run:
    python -m pip install pygame
    python dungeon_pong_playtest_v2.py
"""

import math
import random
import sys

import pygame

pygame.init()

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

WIDTH, HEIGHT = 1100, 680
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dungeon Pong")
clock = pygame.time.Clock()

ARENA = pygame.Rect(55, 105, WIDTH - 110, HEIGHT - 155)
PLAYER_X = ARENA.left + 28
ENEMY_X = ARENA.right - 42

BLACK = (5, 5, 6)
PANEL = (12, 12, 14)
WHITE = (242, 242, 242)
GRAY = (120, 120, 126)
DARK_GRAY = (42, 42, 47)
CYAN = (45, 246, 255)
GREEN = (90, 255, 155)
RED = (255, 55, 90)
GOLD = (255, 224, 80)
VIOLET = (210, 90, 255)

TITLE_FONT = pygame.font.SysFont("arial", 58, bold=True)
MENU_FONT = pygame.font.SysFont("arial", 27, bold=True)
HUD_FONT = pygame.font.SysFont("arial", 20, bold=True)
SMALL_FONT = pygame.font.SysFont("arial", 15, bold=True)
ROOM_FONT = pygame.font.SysFont("arial", 34, bold=True)
ABILITY_FONT = pygame.font.SysFont("arial", 18, bold=True)

PLAYER_SPEED = 520
PLAYER_H = 108
PADDLE_W = 14
BALL_RADIUS = 9
BALL_START_SPEED = 430
BALL_MAX_SPEED = 700
PLAYER_MAX_HP = 3

ENEMIES = [
    # Ability: every third return sharply changes the ball's vertical direction.
    {"name": "SLIME", "hp": 2, "paddle_h": 112, "speed": 270, "error": 115, "accent": GREEN},
    # Ability: every third incoming shot temporarily grows its paddle.
    {"name": "SKELETON", "hp": 3, "paddle_h": 98, "speed": 300, "error": 92, "accent": GOLD},
    # Ability: every third return briefly phases the ball out of sight.
    {"name": "WRAITH", "hp": 3, "paddle_h": 86, "speed": 322, "error": 78, "accent": VIOLET},
    # Ability: every fourth return summons a one-hit wall near center court.
    {"name": "NECROMANCER", "hp": 4, "paddle_h": 82, "speed": 336, "error": 70, "accent": RED},
]

POWERUPS = [
    ("BLINK", "SPACE DASH"),
    ("SHOCK", "3RD HIT STUNS"),
    ("REFLECT", "PARRY HAZARDS"),
    ("RICOCHET", "WALLS BEND SHOTS"),
]

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_text(text, font, color, pos, anchor="center"):
    image = font.render(str(text), True, color)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    screen.blit(image, rect)
    return rect


def rounded_rect(rect, fill, radius=10, width=0, border=None):
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(screen, border, rect, width=max(1, width), border_radius=radius)


def predict_y(start_x, start_y, vx, vy, target_x):
    """Predict ball center Y at target_x, including top/bottom bounces."""
    if abs(vx) < 0.001:
        return start_y
    t = (target_x - start_x) / vx
    if t <= 0:
        return start_y

    raw_y = start_y + vy * t
    top = ARENA.top + BALL_RADIUS
    bottom = ARENA.bottom - BALL_RADIUS
    span = bottom - top
    if span <= 0:
        return start_y

    n = (raw_y - top) % (2 * span)
    if n > span:
        n = 2 * span - n
    return top + n


class Particle:
    def __init__(self, x, y, color, speed=220, life=0.22):
        angle = random.random() * math.tau
        speed *= random.uniform(0.45, 1.0)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = life * random.uniform(0.65, 1.0)
        self.max_life = self.life
        self.color = color

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.93
        self.vy *= 0.93

    def draw(self):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        r = max(1, int(3 * t))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r)


class Button:
    def __init__(self, text, center, width=245, subtext=None):
        self.text = text
        self.subtext = subtext
        self.rect = pygame.Rect(0, 0, width, 60 if subtext else 52)
        self.rect.center = center

    def draw(self, selected=False):
        fill = (24, 24, 27) if selected else PANEL
        border = WHITE if selected else DARK_GRAY
        rounded_rect(self.rect, fill, 8, 2, border)
        if self.subtext:
            draw_text(self.text, HUD_FONT, WHITE if selected else GRAY, (self.rect.centerx, self.rect.centery - 9))
            draw_text(self.subtext, SMALL_FONT, GRAY, (self.rect.centerx, self.rect.centery + 15))
        else:
            draw_text(self.text, MENU_FONT, WHITE if selected else GRAY, self.rect.center)

    def hit(self, pos):
        return self.rect.collidepoint(pos)


# -----------------------------------------------------------------------------
# Game
# -----------------------------------------------------------------------------


class Game:
    def __init__(self):
        self.state = "menu"
        self.menu_index = 0
        self.pause_index = 0
        self.end_index = 0
        self.power_index = 0
        self.power_choices = []
        self.pending_room = None
        self.particles = []
        self.flash = 0.0
        self.flash_color = WHITE
        self.shake = 0.0
        self.reset_run()

    def reset_run(self):
        self.room = 0
        self.player_hp = PLAYER_MAX_HP
        self.player_speed = PLAYER_SPEED
        self.player_height = PLAYER_H
        self.shields = 0

        # Player powers persist for the run.
        self.has_blink = False
        self.has_shock = False
        self.has_reflect = False
        self.has_ricochet = False
        self.blink_cooldown = 0.0
        self.player_return_count = 0
        self.shock_shot = False
        self.ricochet_shot = False

        self.player = pygame.Rect(PLAYER_X, ARENA.centery - PLAYER_H // 2, PADDLE_W, PLAYER_H)
        self.enemy = pygame.Rect(ENEMY_X, ARENA.centery - 50, PADDLE_W, 100)
        self.enemy_hp = 0

        self.ball_x = ARENA.centerx
        self.ball_y = ARENA.centery
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.serve_timer = 0.0
        self.room_intro = 0.0

        self.ai_target = ARENA.centery
        self.ai_has_read = False

        self.enemy_hit_count = 0
        self.incoming_count = 0
        self.guard_timer = 0.0
        self.enemy_stun = 0.0
        self.phase_pending = False
        self.ball_hidden_timer = 0.0
        self.phantom_cooldown = 0.0
        self.phantom_charge = 0.0
        self.phantom_target = None
        self.arrow_charge = 0.0
        self.arrow_target_y = None
        self.skull_charge = 0.0
        self.wall_timer = 0.0
        self.wall_rect = None
        self.wall_touch_cooldown = 0.0
        self.projectiles = []
        self.slime_bounces = 0

        self.ability_text = ""
        self.ability_timer = 0.0
        self.start_room(0)

    @property
    def enemy_data(self):
        return ENEMIES[self.room]

    def set_enemy_height(self, h):
        cy = self.enemy.centery
        self.enemy.height = int(h)
        self.enemy.centery = clamp(cy, ARENA.top + self.enemy.height // 2, ARENA.bottom - self.enemy.height // 2)

    def start_room(self, index):
        self.room = index
        data = self.enemy_data
        self.enemy_hp = data["hp"]
        self.enemy.height = data["paddle_h"]
        self.enemy.centery = ARENA.centery

        self.player.height = int(self.player_height)
        self.player.centery = ARENA.centery

        self.enemy_hit_count = 0
        self.incoming_count = 0
        self.guard_timer = 0.0
        self.enemy_stun = 0.0
        self.phase_pending = False
        self.ball_hidden_timer = 0.0
        self.phantom_cooldown = 1.5
        self.phantom_charge = 0.0
        self.phantom_target = None
        self.arrow_charge = 0.0
        self.arrow_target_y = None
        self.skull_charge = 0.0
        self.wall_timer = 0.0
        self.wall_rect = None
        self.projectiles = []
        self.slime_bounces = 0
        self.shock_shot = False
        self.ricochet_shot = False
        self.room_intro = 0.9
        self.reset_ball(direction=random.choice((-1, 1)))

    def cap_ball_speed(self):
        speed = math.hypot(self.ball_vx, self.ball_vy)
        if speed > BALL_MAX_SPEED and speed > 0:
            scale = BALL_MAX_SPEED / speed
            self.ball_vx *= scale
            self.ball_vy *= scale

    def reset_ball(self, direction=None):
        if direction is None:
            direction = random.choice((-1, 1))
        self.ball_x = ARENA.centerx
        self.ball_y = ARENA.centery
        angle = math.radians(random.uniform(-24, 24))
        self.ball_vx = math.cos(angle) * BALL_START_SPEED * direction
        self.ball_vy = math.sin(angle) * BALL_START_SPEED
        self.serve_timer = 0.6
        self.ai_has_read = False
        self.ball_hidden_timer = 0.0
        self.phase_pending = False
        self.wall_touch_cooldown = 0.0
        self.slime_bounces = 0
        self.shock_shot = False
        self.ricochet_shot = False
        if self.ball_vx > 0:
            self.commit_ai_read()

    def commit_ai_read(self):
        data = self.enemy_data
        ideal = predict_y(self.ball_x, self.ball_y, self.ball_vx, self.ball_vy, self.enemy.left)
        mistake = random.uniform(-data["error"], data["error"])
        self.ai_target = clamp(
            ideal + mistake,
            ARENA.top + self.enemy.height / 2,
            ARENA.bottom - self.enemy.height / 2,
        )
        self.ai_has_read = True

    def announce(self, text, color):
        self.ability_text = text
        self.ability_timer = 0.65
        self.flash = max(self.flash, 0.035)
        self.flash_color = color

    def burst(self, x, y, color, count=12, strength=230):
        for _ in range(count):
            self.particles.append(Particle(x, y, color, strength))
        self.flash = 0.055
        self.flash_color = color

    def start_game(self):
        self.reset_run()
        self.state = "play"

    # ------------------------------------------------------------------
    # Player powerups
    # ------------------------------------------------------------------

    def open_powerup(self, next_room):
        self.pending_room = next_room
        owned = {
            "BLINK": self.has_blink,
            "SHOCK": self.has_shock,
            "REFLECT": self.has_reflect,
            "RICOCHET": self.has_ricochet,
        }
        available = [power for power in POWERUPS if not owned[power[0]]]
        self.power_choices = random.sample(available, 2)
        self.power_index = 0
        self.state = "powerup"

    def apply_powerup(self, name):
        if name == "BLINK":
            self.has_blink = True
        elif name == "SHOCK":
            self.has_shock = True
        elif name == "REFLECT":
            self.has_reflect = True
        elif name == "RICOCHET":
            self.has_ricochet = True

        self.start_room(self.pending_room)
        self.pending_room = None
        self.state = "play"

    # ------------------------------------------------------------------
    # Hits / monster abilities
    # ------------------------------------------------------------------

    def player_hit(self):
        offset = (self.ball_y - self.player.centery) / (self.player.height / 2)
        offset = clamp(offset, -1, 1)
        speed = min(BALL_MAX_SPEED, math.hypot(self.ball_vx, self.ball_vy) * 1.025)
        self.ball_vx = abs(speed * 0.92)
        self.ball_vy = speed * 0.72 * offset
        self.ball_x = self.player.right + BALL_RADIUS + 1

        self.incoming_count += 1
        self.player_return_count += 1
        self.ricochet_shot = self.has_ricochet

        # SHOCK: every third player return becomes a stun shot.
        if self.has_shock and self.player_return_count % 3 == 0:
            self.shock_shot = True
            self.burst(self.ball_x, self.ball_y, CYAN, 16, 260)
        else:
            self.shock_shot = False

        # SKELETON: every third incoming shot grows a much larger guard for longer.
        if self.room == 1 and self.incoming_count % 3 == 0:
            self.guard_timer = 2.45
            self.set_enemy_height(self.enemy_data["paddle_h"] * 1.75)
            self.announce("BONE GUARD", GOLD)
            self.burst(self.enemy.centerx, self.enemy.centery, GOLD, 18, 250)

        self.commit_ai_read()
        self.burst(self.ball_x, self.ball_y, CYAN, 8, 190)

    def enemy_hit(self):
        offset = (self.ball_y - self.enemy.centery) / (self.enemy.height / 2)
        offset = clamp(offset, -1, 1)
        speed = min(BALL_MAX_SPEED, math.hypot(self.ball_vx, self.ball_vy) * 1.018)
        self.ball_vx = -abs(speed * 0.92)
        self.ball_vy = speed * 0.70 * offset
        self.ball_x = self.enemy.left - BALL_RADIUS - 1
        self.ai_has_read = False
        self.enemy_hit_count += 1
        accent = self.enemy_data["accent"]
        self.burst(self.ball_x, self.ball_y, accent, 8, 190)

        if self.shock_shot:
            self.enemy_stun = max(self.enemy_stun, 0.55)
            self.shock_shot = False
            self.announce("SHOCK", CYAN)
            self.burst(self.enemy.centerx, self.enemy.centery, CYAN, 22, 300)

        # SLIME: coats the orb. Its next two wall bounces become extra springy.
        if self.room == 0 and self.enemy_hit_count % 3 == 0:
            self.slime_bounces = 2
            self.announce("SLIME COAT", GREEN)
            self.burst(self.ball_x, self.ball_y, GREEN, 20, 285)

        # SKELETON: fires an aimed arrow after a short tell.
        if self.room == 1 and self.enemy_hit_count % 4 == 0 and self.arrow_charge <= 0:
            self.arrow_target_y = self.player.centery
            self.arrow_charge = 0.60
            self.announce("ARROW", GOLD)

        # WRAITH: every third return briefly hides the ball after center court.
        if self.room == 2 and self.enemy_hit_count % 3 == 0:
            self.phase_pending = True
            self.announce("PHASE", VIOLET)

        # NECROMANCER: a wall on the player's half violently redirects the incoming orb.
        if self.room == 3 and self.enemy_hit_count % 4 == 0:
            wall_h = 150
            wall_x = int(ARENA.left + ARENA.width * 0.42)
            intercept = predict_y(self.ball_x, self.ball_y, self.ball_vx, self.ball_vy, wall_x)
            wall_y = clamp(int(intercept - wall_h / 2), ARENA.top + 15, ARENA.bottom - wall_h - 15)
            self.wall_rect = pygame.Rect(wall_x - 7, wall_y, 14, wall_h)
            self.wall_timer = 3.0
            self.announce("BONE WALL", RED)
            self.burst(self.wall_rect.centerx, self.wall_rect.centery, RED, 20, 260)

        # NECROMANCER: every fifth return charges a pair of hostile soul-orbs.
        if self.room == 3 and self.enemy_hit_count % 3 == 0 and self.skull_charge <= 0:
            self.skull_charge = 0.55
            self.announce("SOUL ORBS", RED)

    def spawn_arrow(self):
        target_y = self.arrow_target_y if self.arrow_target_y is not None else self.player.centery
        dx = self.player.centerx - self.enemy.centerx
        dy = target_y - self.enemy.centery
        length = max(1.0, math.hypot(dx, dy))
        speed = 520.0
        self.projectiles.append({
            "kind": "arrow", "x": float(self.enemy.left - 10), "y": float(self.enemy.centery),
            "vx": dx / length * speed, "vy": dy / length * speed, "r": 7, "owner": "enemy", "color": GOLD
        })
        self.burst(self.enemy.left, self.enemy.centery, GOLD, 18, 300)

    def spawn_soul_orbs(self):
        for offset in (-55, 55):
            target_y = clamp(self.player.centery + offset, ARENA.top + 20, ARENA.bottom - 20)
            dx = self.player.centerx - self.enemy.centerx
            dy = target_y - self.enemy.centery
            length = max(1.0, math.hypot(dx, dy))
            speed = 330.0
            self.projectiles.append({
                "kind": "soul", "x": float(self.enemy.left - 14), "y": float(self.enemy.centery),
                "vx": dx / length * speed, "vy": dy / length * speed, "r": 9, "owner": "enemy", "color": RED
            })
        self.burst(self.enemy.left, self.enemy.centery, RED, 26, 320)

    def hazard_hit_player(self, color):
        self.player_hp -= 1
        self.burst(self.player.centerx, self.player.centery, color, 26, 330)
        self.shake = 0.10
        if self.player_hp <= 0:
            self.state = "defeat"
            self.end_index = 0

    def update_projectiles(self, dt):
        survivors = []
        for p in self.projectiles:
            # Soul orbs subtly home while still far from the player.
            if p["kind"] == "soul" and p["owner"] == "enemy" and p["x"] > self.player.right + 130:
                desired = clamp((self.player.centery - p["y"]) * 1.9, -145, 145)
                p["vy"] += (desired - p["vy"]) * min(1.0, dt * 2.2)

            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt

            # Arena top/bottom bounce.
            if p["y"] <= ARENA.top + p["r"]:
                p["y"] = ARENA.top + p["r"]
                p["vy"] = abs(p["vy"])
            elif p["y"] >= ARENA.bottom - p["r"]:
                p["y"] = ARENA.bottom - p["r"]
                p["vy"] = -abs(p["vy"])

            rect = pygame.Rect(int(p["x"] - p["r"]), int(p["y"] - p["r"]), p["r"] * 2, p["r"] * 2)

            if p["owner"] == "enemy" and rect.colliderect(self.player):
                if self.has_reflect:
                    p["owner"] = "player"
                    p["vx"] = abs(p["vx"]) * 1.18
                    p["vy"] *= -0.35
                    p["color"] = CYAN
                    self.burst(p["x"], p["y"], CYAN, 18, 300)
                    survivors.append(p)
                elif p["kind"] == "soul":
                    # Soul-orbs are destroyed by one paddle bounce.
                    self.burst(p["x"], p["y"], VIOLET, 16, 260)
                else:
                    # Arrows hurt on contact; dodge them unless REFLECT is owned.
                    self.hazard_hit_player(GOLD)
                continue

            if p["owner"] == "player" and rect.colliderect(self.enemy):
                self.enemy_stun = max(self.enemy_stun, 0.65)
                self.burst(p["x"], p["y"], CYAN, 20, 300)
                continue

            if p["owner"] == "enemy" and p["x"] < ARENA.left - 25:
                if p["kind"] == "soul":
                    self.hazard_hit_player(RED)
                # Missed arrows are simply dodged.
                continue
            if p["owner"] == "player" and p["x"] > ARENA.right + 25:
                continue

            survivors.append(p)

        self.projectiles = survivors

    def damage_enemy(self):
        self.enemy_hp -= 1
        self.burst(ARENA.right - 8, self.ball_y, self.enemy_data["accent"], 22, 320)
        self.shake = 0.09
        if self.enemy_hp <= 0:
            if self.room >= len(ENEMIES) - 1:
                self.state = "victory"
                self.end_index = 0
                return
            self.open_powerup(self.room + 1)
        else:
            self.reset_ball(direction=-1)

    def damage_player(self):
        if self.shields > 0:
            self.shields -= 1
            self.announce("BLOCK", CYAN)
            self.burst(ARENA.left + 8, self.ball_y, CYAN, 24, 320)
            self.shake = 0.07
            self.reset_ball(direction=1)
            return

        self.player_hp -= 1
        self.burst(ARENA.left + 8, self.ball_y, RED, 22, 320)
        self.shake = 0.09
        if self.player_hp <= 0:
            self.state = "defeat"
            self.end_index = 0
        else:
            self.reset_ball(direction=1)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_ai(self, dt):
        data = self.enemy_data
        if self.enemy_stun > 0:
            return

        if self.ball_vx > 0:
            if not self.ai_has_read:
                self.commit_ai_read()
            target = self.ai_target
        else:
            target = ARENA.centery

        # WRAITH emergency Phantom Step: only when a genuinely hard shot is already close.
        if (self.room == 2 and self.ball_vx > 0 and self.phantom_cooldown <= 0 and
                self.phantom_charge <= 0 and self.ball_x > ARENA.centerx + 115):
            ideal = predict_y(self.ball_x, self.ball_y, self.ball_vx, self.ball_vy, self.enemy.left)
            if abs(ideal - self.enemy.centery) > 125:
                self.phantom_target = clamp(ideal, ARENA.top + self.enemy.height / 2, ARENA.bottom - self.enemy.height / 2)
                self.phantom_charge = 0.28
                self.phantom_cooldown = 5.2
                self.announce("PHANTOM STEP", VIOLET)

        center = self.enemy.centery
        deadzone = 12
        speed = data["speed"]
        if center < target - deadzone:
            self.enemy.y += speed * dt
        elif center > target + deadzone:
            self.enemy.y -= speed * dt

        self.enemy.y = clamp(self.enemy.y, ARENA.top, ARENA.bottom - self.enemy.height)

    def update_abilities(self, dt):
        self.guard_timer = max(0.0, self.guard_timer - dt)
        self.enemy_stun = max(0.0, self.enemy_stun - dt)
        self.ball_hidden_timer = max(0.0, self.ball_hidden_timer - dt)
        self.wall_touch_cooldown = max(0.0, self.wall_touch_cooldown - dt)
        self.phantom_cooldown = max(0.0, self.phantom_cooldown - dt)
        self.blink_cooldown = max(0.0, self.blink_cooldown - dt)

        if self.room == 1 and self.guard_timer <= 0 and self.enemy.height != self.enemy_data["paddle_h"]:
            self.set_enemy_height(self.enemy_data["paddle_h"])

        if self.arrow_charge > 0:
            self.arrow_charge -= dt
            if self.arrow_charge <= 0:
                self.spawn_arrow()
                self.arrow_target_y = None

        if self.skull_charge > 0:
            self.skull_charge -= dt
            if self.skull_charge <= 0:
                self.spawn_soul_orbs()

        if self.phantom_charge > 0:
            self.phantom_charge -= dt
            if self.phantom_charge <= 0 and self.phantom_target is not None:
                self.enemy.centery = int(self.phantom_target)
                self.enemy.y = clamp(self.enemy.y, ARENA.top, ARENA.bottom - self.enemy.height)
                self.burst(self.enemy.centerx, self.enemy.centery, VIOLET, 24, 330)
                self.phantom_target = None

        if self.phase_pending and self.ball_vx < 0 and self.ball_x <= ARENA.centerx:
            self.phase_pending = False
            self.ball_hidden_timer = 0.32
            self.burst(self.ball_x, self.ball_y, VIOLET, 10, 180)

        if self.wall_timer > 0:
            self.wall_timer -= dt
            if self.wall_timer <= 0:
                self.wall_rect = None
        else:
            self.wall_rect = None

    def update_play(self, dt):
        keys = pygame.key.get_pressed()
        move = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move += 1
        self.player.y += move * self.player_speed * dt
        self.player.y = clamp(self.player.y, ARENA.top, ARENA.bottom - self.player.height)

        self.update_ai(dt)
        self.update_abilities(dt)
        self.update_projectiles(dt)

        if self.room_intro > 0:
            self.room_intro -= dt
            return
        if self.serve_timer > 0:
            self.serve_timer -= dt
            return

        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        top = ARENA.top + BALL_RADIUS
        bottom = ARENA.bottom - BALL_RADIUS
        if self.ball_y <= top:
            self.ball_y = top
            self.ball_vy = abs(self.ball_vy)
            if self.slime_bounces > 0 and self.ball_vx < 0:
                self.slime_bounces -= 1
                self.ball_vy *= 1.30
                self.ball_vx *= 1.06
                self.burst(self.ball_x, self.ball_y, GREEN, 14, 240)
            if self.ricochet_shot and self.ball_vx > 0:
                self.ball_vy *= 1.18
                self.ball_vx *= 1.04
                self.burst(self.ball_x, self.ball_y, CYAN, 12, 220)
            self.cap_ball_speed()
        elif self.ball_y >= bottom:
            self.ball_y = bottom
            self.ball_vy = -abs(self.ball_vy)
            if self.slime_bounces > 0 and self.ball_vx < 0:
                self.slime_bounces -= 1
                self.ball_vy *= 1.30
                self.ball_vx *= 1.06
                self.burst(self.ball_x, self.ball_y, GREEN, 14, 240)
            if self.ricochet_shot and self.ball_vx > 0:
                self.ball_vy *= 1.18
                self.ball_vx *= 1.04
                self.burst(self.ball_x, self.ball_y, CYAN, 12, 220)
            self.cap_ball_speed()

        ball_rect = pygame.Rect(
            int(self.ball_x - BALL_RADIUS),
            int(self.ball_y - BALL_RADIUS),
            BALL_RADIUS * 2,
            BALL_RADIUS * 2,
        )

        # Necromancer wall only alters the boss's incoming attack; player shots pass through it.
        if (self.wall_rect and self.wall_touch_cooldown <= 0 and self.ball_vx < 0
                and ball_rect.colliderect(self.wall_rect)):
            self.ball_x = self.wall_rect.left - BALL_RADIUS - 1
            speed = min(BALL_MAX_SPEED, math.hypot(self.ball_vx, self.ball_vy) * 1.12)
            self.ball_vx = -abs(speed * 0.86)
            kick = random.choice((-1, 1)) * random.uniform(250, 340)
            self.ball_vy = clamp(self.ball_vy + kick, -BALL_MAX_SPEED * 0.92, BALL_MAX_SPEED * 0.92)
            self.wall_touch_cooldown = 0.15
            self.burst(self.wall_rect.centerx, self.ball_y, RED, 26, 340)
            self.wall_rect = None
            self.wall_timer = 0.0

        ball_rect = pygame.Rect(
            int(self.ball_x - BALL_RADIUS),
            int(self.ball_y - BALL_RADIUS),
            BALL_RADIUS * 2,
            BALL_RADIUS * 2,
        )

        if self.ball_vx < 0 and ball_rect.colliderect(self.player):
            self.player_hit()
        elif self.ball_vx > 0 and ball_rect.colliderect(self.enemy):
            self.enemy_hit()

        if self.ball_x < ARENA.left - BALL_RADIUS * 2:
            self.damage_player()
        elif self.ball_x > ARENA.right + BALL_RADIUS * 2:
            self.damage_enemy()

    def update(self, dt):
        if self.state == "play":
            self.update_play(dt)

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        self.flash = max(0, self.flash - dt)
        self.shake = max(0, self.shake - dt)
        self.ability_timer = max(0, self.ability_timer - dt)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if self.state == "menu":
                if event.key in (pygame.K_w, pygame.K_UP):
                    self.menu_index = (self.menu_index - 1) % 2
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self.menu_index = (self.menu_index + 1) % 2
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.menu_index == 0:
                        self.start_game()
                    else:
                        pygame.quit(); sys.exit()

            elif self.state == "play":
                if event.key == pygame.K_SPACE and self.has_blink and self.blink_cooldown <= 0:
                    old_y = self.player.centery
                    target = clamp(self.ball_y, ARENA.top + self.player.height / 2, ARENA.bottom - self.player.height / 2)
                    delta = clamp(target - self.player.centery, -155, 155)
                    self.player.centery += int(delta)
                    self.player.y = clamp(self.player.y, ARENA.top, ARENA.bottom - self.player.height)
                    self.blink_cooldown = 4.0
                    self.burst(self.player.centerx, old_y, CYAN, 16, 260)
                    self.burst(self.player.centerx, self.player.centery, CYAN, 18, 280)
                elif event.key == pygame.K_ESCAPE:
                    self.state = "pause"
                    self.pause_index = 0
                elif event.key == pygame.K_r:
                    self.start_game()

            elif self.state == "powerup":
                if event.key in (pygame.K_a, pygame.K_LEFT, pygame.K_w, pygame.K_UP):
                    self.power_index = (self.power_index - 1) % 2
                elif event.key in (pygame.K_d, pygame.K_RIGHT, pygame.K_s, pygame.K_DOWN):
                    self.power_index = (self.power_index + 1) % 2
                elif event.key == pygame.K_1:
                    self.apply_powerup(self.power_choices[0][0])
                elif event.key == pygame.K_2:
                    self.apply_powerup(self.power_choices[1][0])
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.apply_powerup(self.power_choices[self.power_index][0])

            elif self.state == "pause":
                if event.key in (pygame.K_w, pygame.K_UP):
                    self.pause_index = (self.pause_index - 1) % 4
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self.pause_index = (self.pause_index + 1) % 4
                elif event.key == pygame.K_ESCAPE:
                    self.state = "play"
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.pause_index == 0:
                        self.state = "play"
                    elif self.pause_index == 1:
                        self.start_game()
                    elif self.pause_index == 2:
                        self.state = "menu"
                        self.menu_index = 0
                    else:
                        pygame.quit(); sys.exit()

            elif self.state in ("victory", "defeat"):
                if event.key in (pygame.K_w, pygame.K_UP):
                    self.end_index = (self.end_index - 1) % 3
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self.end_index = (self.end_index + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.end_index == 0:
                        self.start_game()
                    elif self.end_index == 1:
                        self.state = "menu"
                        self.menu_index = 0
                    else:
                        pygame.quit(); sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.state == "menu":
                for i, b in enumerate(self.menu_buttons()):
                    if b.hit(pos):
                        self.menu_index = i
                        if i == 0:
                            self.start_game()
                        else:
                            pygame.quit(); sys.exit()

            elif self.state == "powerup":
                for i, b in enumerate(self.power_buttons()):
                    if b.hit(pos):
                        self.power_index = i
                        self.apply_powerup(self.power_choices[i][0])
                        break

            elif self.state == "pause":
                for i, b in enumerate(self.pause_buttons()):
                    if b.hit(pos):
                        self.pause_index = i
                        if i == 0:
                            self.state = "play"
                        elif i == 1:
                            self.start_game()
                        elif i == 2:
                            self.state = "menu"
                            self.menu_index = 0
                        else:
                            pygame.quit(); sys.exit()

            elif self.state in ("victory", "defeat"):
                for i, b in enumerate(self.end_buttons()):
                    if b.hit(pos):
                        self.end_index = i
                        if i == 0:
                            self.start_game()
                        elif i == 1:
                            self.state = "menu"
                            self.menu_index = 0
                        else:
                            pygame.quit(); sys.exit()

        if event.type == pygame.MOUSEMOTION:
            pos = event.pos
            if self.state == "menu":
                for i, b in enumerate(self.menu_buttons()):
                    if b.hit(pos):
                        self.menu_index = i
            elif self.state == "powerup":
                for i, b in enumerate(self.power_buttons()):
                    if b.hit(pos):
                        self.power_index = i
            elif self.state == "pause":
                for i, b in enumerate(self.pause_buttons()):
                    if b.hit(pos):
                        self.pause_index = i
            elif self.state in ("victory", "defeat"):
                for i, b in enumerate(self.end_buttons()):
                    if b.hit(pos):
                        self.end_index = i

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def menu_buttons(self):
        return [
            Button("PLAY", (WIDTH // 2, 360)),
            Button("QUIT", (WIDTH // 2, 430)),
        ]

    def power_buttons(self):
        if len(self.power_choices) < 2:
            return []
        return [
            Button(self.power_choices[0][0], (WIDTH // 2 - 150, 390), 240, self.power_choices[0][1]),
            Button(self.power_choices[1][0], (WIDTH // 2 + 150, 390), 240, self.power_choices[1][1]),
        ]

    def pause_buttons(self):
        return [
            Button("RESUME", (WIDTH // 2, 310)),
            Button("RESTART", (WIDTH // 2, 375)),
            Button("MENU", (WIDTH // 2, 440)),
            Button("QUIT", (WIDTH // 2, 505)),
        ]

    def end_buttons(self):
        return [
            Button("RESTART", (WIDTH // 2, 365)),
            Button("MENU", (WIDTH // 2, 430)),
            Button("QUIT", (WIDTH // 2, 495)),
        ]

    def draw_background(self):
        screen.fill(BLACK)
        for y in range(0, HEIGHT, 54):
            pygame.draw.line(screen, (10, 10, 12), (0, y), (WIDTH, y), 1)
        for x in range(0, WIDTH, 110):
            pygame.draw.line(screen, (8, 8, 10), (x, 0), (x, HEIGHT), 1)

    def draw_menu(self):
        draw_text("DUNGEON PONG", TITLE_FONT, WHITE, (WIDTH // 2, 225))
        for i, button in enumerate(self.menu_buttons()):
            button.draw(i == self.menu_index)

    def draw_hud(self):
        draw_text(f"HP  {self.player_hp}", HUD_FONT, WHITE, (ARENA.left, 58), "midleft")

        # Small shield diamonds beside HP; no extra explanatory text.
        for i in range(self.shields):
            x = ARENA.left + 77 + i * 18
            pygame.draw.polygon(screen, CYAN, [(x, 51), (x + 7, 58), (x, 65), (x - 7, 58)], 2)

        draw_text(f"ROOM  {self.room + 1}/{len(ENEMIES)}", HUD_FONT, GRAY, (WIDTH // 2, 58))
        draw_text(f"{self.enemy_data['name']}  {self.enemy_hp}", HUD_FONT, WHITE, (ARENA.right, 58), "midright")
        if self.has_blink:
            blink_text = "BLINK" if self.blink_cooldown <= 0 else f"BLINK {self.blink_cooldown:.1f}"
            draw_text(blink_text, SMALL_FONT, CYAN if self.blink_cooldown <= 0 else GRAY, (ARENA.left, 84), "midleft")

    def draw_arena(self):
        pygame.draw.rect(screen, DARK_GRAY, ARENA, 2)
        for y in range(ARENA.top + 10, ARENA.bottom, 28):
            pygame.draw.line(
                screen,
                (37, 37, 41),
                (ARENA.centerx, y),
                (ARENA.centerx, min(y + 12, ARENA.bottom)),
                2,
            )

        pygame.draw.rect(screen, WHITE, self.player, border_radius=4)

        enemy_color = (195, 195, 198)
        if self.room == 1 and self.guard_timer > 0:
            enemy_color = GOLD
        pygame.draw.rect(screen, enemy_color, self.enemy, border_radius=4)

        # Minimal enemy marks.
        c = self.enemy.center
        if self.room == 0:
            pygame.draw.circle(screen, (100, 100, 104), (c[0], self.enemy.top - 12), 6, 1)
        elif self.room == 1:
            pygame.draw.line(screen, (100, 100, 104), (c[0] - 7, self.enemy.top - 15), (c[0] + 7, self.enemy.top - 5), 2)
            pygame.draw.line(screen, (100, 100, 104), (c[0] + 7, self.enemy.top - 15), (c[0] - 7, self.enemy.top - 5), 2)
        elif self.room == 2:
            pygame.draw.circle(screen, (100, 100, 104), (c[0], self.enemy.top - 11), 8, 1)
        else:
            pygame.draw.polygon(
                screen,
                (100, 100, 104),
                [(c[0], self.enemy.top - 22), (c[0] - 8, self.enemy.top - 8), (c[0] + 8, self.enemy.top - 8)],
                1,
            )

        if self.wall_rect:
            pygame.draw.rect(screen, RED, self.wall_rect, 2, border_radius=3)
            for y in range(self.wall_rect.top + 8, self.wall_rect.bottom, 18):
                pygame.draw.line(screen, RED, (self.wall_rect.left + 3, y), (self.wall_rect.right - 3, y), 1)

        if self.phantom_charge > 0 and self.phantom_target is not None:
            ghost = pygame.Rect(self.enemy.x, int(self.phantom_target - self.enemy.height / 2), self.enemy.width, self.enemy.height)
            pygame.draw.rect(screen, VIOLET, ghost, 1, border_radius=4)

        if self.arrow_charge > 0 and self.arrow_target_y is not None:
            pygame.draw.line(screen, GOLD, (self.enemy.left, self.enemy.centery), (self.player.right + 25, int(self.arrow_target_y)), 1)
            pygame.draw.circle(screen, GOLD, (self.player.right + 18, int(self.arrow_target_y)), 8, 1)

        for pr in self.projectiles:
            x, y = int(pr["x"]), int(pr["y"])
            if pr["kind"] == "arrow":
                direction = 1 if pr["vx"] > 0 else -1
                pygame.draw.line(screen, pr["color"], (x - 14 * direction, y), (x + 8 * direction, y), 3)
                pygame.draw.polygon(screen, pr["color"], [(x + 10 * direction, y), (x + 2 * direction, y - 5), (x + 2 * direction, y + 5)])
            else:
                pygame.draw.circle(screen, pr["color"], (x, y), pr["r"], 2)
                pygame.draw.circle(screen, WHITE if pr["owner"] == "enemy" else CYAN, (x, y), 2)

        if self.ball_hidden_timer <= 0:
            if self.slime_bounces > 0:
                pygame.draw.circle(screen, GREEN, (int(self.ball_x), int(self.ball_y)), BALL_RADIUS + 4, 2)
            if self.shock_shot:
                pygame.draw.circle(screen, CYAN, (int(self.ball_x), int(self.ball_y)), BALL_RADIUS + 4, 2)
            pygame.draw.circle(screen, WHITE, (int(self.ball_x), int(self.ball_y)), BALL_RADIUS)

        for p in self.particles:
            p.draw()

        if self.room == 0 and self.room_intro > 0:
            draw_text("W/S or ↑↓", SMALL_FONT, GRAY, (WIDTH // 2, ARENA.bottom + 27))

        if self.room_intro > 0:
            draw_text(self.enemy_data["name"], ROOM_FONT, WHITE, ARENA.center)

        if self.ability_timer > 0:
            alpha_scale = min(1.0, self.ability_timer / 0.18)
            color = self.enemy_data["accent"] if self.ability_text != "BLOCK" else CYAN
            if alpha_scale < 0.5:
                color = tuple(int(c * (0.45 + alpha_scale)) for c in color)
            draw_text(self.ability_text, ABILITY_FONT, color, (WIDTH // 2, ARENA.top + 24))

    def draw_play(self):
        self.draw_hud()
        self.draw_arena()

    def draw_powerup(self):
        # Keep the arena faintly visible under the choice screen.
        self.draw_hud()
        self.draw_arena()
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 210))
        screen.blit(shade, (0, 0))
        draw_text("POWER UP", ROOM_FONT, WHITE, (WIDTH // 2, 285))
        for i, b in enumerate(self.power_buttons()):
            b.draw(i == self.power_index)

    def draw_overlay(self, title, buttons, selected):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 205))
        screen.blit(shade, (0, 0))
        draw_text(title, TITLE_FONT, WHITE, (WIDTH // 2, 205))
        for i, b in enumerate(buttons):
            b.draw(i == selected)

    def draw(self):
        self.draw_background()

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "powerup":
            self.draw_powerup()
        else:
            self.draw_play()
            if self.state == "pause":
                self.draw_overlay("PAUSED", self.pause_buttons(), self.pause_index)
            elif self.state == "victory":
                self.draw_overlay("DUNGEON CLEARED", self.end_buttons(), self.end_index)
            elif self.state == "defeat":
                self.draw_overlay("DEFEATED", self.end_buttons(), self.end_index)

        if self.flash > 0:
            alpha = int(65 * (self.flash / 0.055))
            fx = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fx.fill((*self.flash_color, alpha))
            screen.blit(fx, (0, 0))


# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------


def main():
    game = Game()
    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.033)
        for event in pygame.event.get():
            game.handle_event(event)
        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()
