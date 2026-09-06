"""Simulation and lifecycle. Rendering lives in ui.py; no display is opened here."""
import math
import random
import pygame
from entities import Ball, Paddle, circle_rect
from encounters import Encounter
from levels import LEVELS, POWER_CHOICES
from save import SaveStore
from settings import (ARENA, PLAYER_X, ENEMY_X, PLAYER_SPEED, PADDLE_W,
                      BALL_RADIUS, BALL_START_SPEED, WHITE, CYAN, RED, GRAY,
                      GOLD, VIOLET, clamp, predict_y)


class Game:
    STEP = 1 / 120

    def __init__(self, save_path=None, seed=None):
        self.store = SaveStore(save_path)
        self.rng = random.Random(seed)
        self.state = "menu"
        self.selection = 0
        self.accumulator = 0
        self.effects = []
        self.powers = set()
        self.power_choices = []
        self.level_index = 0
        self.player_hp = 3
        self.invulnerability = 0
        self.cooldown = 0
        self.hit_freeze = 0
        self.move_input = 0
        self.balls, self.enemies, self.projectiles, self.obstacles = [], [], [], []
        self.player = Paddle(PLAYER_X, ARENA.centery)
        self.bounds = ARENA.copy()
        self.encounter = Encounter(LEVELS[0])
        self.intro = 0
        self.notice = ""
        self.combat_notice = ""
        self.combat_notice_color = WHITE
        self.combat_notice_timer = 0
        self.rally = self.enemy_returns = 0
        self.level_damage = 0
        self.return_count = 0

    @property
    def config(self):
        return LEVELS[self.level_index]

    @property
    def direction(self):
        return -1 if self.config.get("reverse") else 1

    @property
    def stats(self):
        return self.store.data["stats"]

    def start(self, mode="new"):
        data = self.store.data
        if mode == "continue":
            level = data["continue_level"]
            self.powers = set(data["equipped_powers"])
        elif mode == "checkpoint":
            level = min(20, data["checkpoint"] + 1)
            self.powers = set(data["checkpoint_powers"])
        else:
            level = 1
            self.powers = set()
        self.load_level(level - 1)
        pending = data["pending_power_level"]
        if mode in ("continue", "checkpoint") and pending and pending + 1 == level:
            self.load_level(pending - 1)
            self.power_choices = [p for p in POWER_CHOICES[pending] if p not in self.powers]
            self.state = "powerup" if self.power_choices else "cleared"

    def load_level(self, index):
        self.level_index = max(0, min(len(LEVELS) - 1, index))
        self.encounter = Encounter(self.config)
        self.player_hp = 3
        self.player = Paddle(PLAYER_X if self.direction == 1 else ENEMY_X, ARENA.centery)
        count = self.config.get("paddles", 1)
        self.enemies = [Paddle(ENEMY_X if self.direction == 1 else PLAYER_X,
                               ARENA.top + ARENA.height * (i + 1) / (count + 1),
                               56 if count > 1 else 88) for i in range(count)]
        if self.config.get("objective") == "survive":
            self.enemies.clear()
        self.enemy_hp = self.config["hp"]
        self.projectiles.clear()
        self.effects.clear()
        self.encounter.configure_arena(self)
        self.invulnerability = self.cooldown = self.hit_freeze = 0
        self.level_damage = self.rally = self.enemy_returns = 0
        self.return_count = 0
        self.intro = 4.0 if index == 0 else 2.8
        self.notice = self.config["hint"]
        self.combat_notice = ""
        self.combat_notice_timer = 0
        self.accumulator = 0
        self.serve()
        self.state = "play"
        self.selection = 0

    def serve(self):
        self.balls = []
        for i in range(self.encounter.rules().get("balls", 1)):
            angle = self.rng.uniform(-.35, .35)
            # Serve toward the opponent; player always gets a readable preparation window.
            self.balls.append(Ball(vx=self.direction * math.cos(angle) * BALL_START_SPEED,
                                   vy=math.sin(angle) * BALL_START_SPEED, delay=.7 + i * .8))

    def impact(self, x, y, color=WHITE):
        if self.store.data["settings"]["effects"]:
            self.effects.append([x, y, color, .18])
            self.effects = self.effects[-24:]

    def callout(self, text, color=WHITE, duration=.8):
        self.combat_notice = text
        self.combat_notice_color = color
        self.combat_notice_timer = duration

    def use_ability(self):
        if self.state != "play" or "BLINK" not in self.powers or self.cooldown > 0 or self.intro > 0:
            return
        incoming = [b for b in self.balls if b.vx * self.direction < 0 and b.delay <= 0]
        target = min(incoming, key=lambda b: abs(b.x - self.player.x), default=None)
        if target is None:
            self.callout("BLINK NEEDS AN INCOMING BALL", GRAY)
            return
        old_y = self.player.y
        intercept = predict_y(target.x, target.y, target.vx, target.vy, self.player.x, self.bounds)
        self.player.move(clamp(intercept - self.player.y, -210, 210), self.bounds)
        self.cooldown = 2.8
        self.invulnerability = max(self.invulnerability, .3)
        self.stats["abilities_used"] += 1
        self.callout("BLINK", CYAN)
        self.impact(self.player.x, old_y, CYAN)
        self.impact(self.player.x, self.player.y, CYAN)

    def hurt(self, rally_miss=False):
        if self.state != "play":
            return
        if self.invulnerability <= 0:
            self.player_hp -= 1
            self.level_damage += 1
            self.stats["damage_taken"] += 1
            self.invulnerability = 1.25
            self.impact(self.player.x, self.player.y, RED)
            if self.player_hp <= 0:
                self.state = "defeat"
                self.selection = 0
                self.stats["deaths"] += 1
                self.stats["losses"] += 1
                self.store.data["continue_level"] = min(20, self.store.data["checkpoint"] + 1)
                self.store.data["equipped_powers"] = sorted(self.store.data["checkpoint_powers"])
                self.store.data["pending_power_level"] = 0
                self.store.flush()
        if rally_miss and self.state == "play":
            self.rally = 0
            self.projectiles.clear()
            self.encounter.warning = 0
            self.encounter.lanes.clear()
            self.encounter.pattern_clock = 2.5
            self.serve()

    def damage_enemy(self):
        if self.state != "play":
            return
        self.enemy_hp -= 1
        self.impact(ENEMY_X if self.direction == 1 else PLAYER_X, self.bounds.centery)
        if self.enemy_hp <= 0:
            self.clear_level()
        else:
            self.encounter.transition(self)

    def clear_level(self):
        if self.state != "play":
            return
        data = self.store.data
        level = self.level_index + 1
        self.stats["wins"] += 1
        self.stats["enemies_defeated"] += self.config.get("paddles", 1)
        if self.level_damage == 0:
            self.stats["perfect_levels"] += 1
        data["highest_level"] = max(data["highest_level"], min(20, level + 1))
        data["continue_level"] = min(20, level + 1)
        data["equipped_powers"] = sorted(self.powers)
        if level % 5 == 0:
            self.stats["bosses_defeated"] += 1
            if level >= data["checkpoint"]:
                data["checkpoint"] = level
                data["checkpoint_powers"] = sorted(self.powers)
            cosmetic = "OUTLINE" if level == 5 else "NOTCHED" if level >= 10 else "SOLID"
            if cosmetic not in data["unlocked_cosmetics"]:
                data["unlocked_cosmetics"].append(cosmetic)
        self.power_choices = [p for p in POWER_CHOICES.get(level, ()) if p not in self.powers]
        data["pending_power_level"] = level if self.power_choices else 0
        if level == 20:
            data["completed"] = True
            self.state = "victory"
        else:
            self.state = "powerup" if self.power_choices else "cleared"
        self.selection = 0
        self.store.flush()

    def choose_power(self, power):
        if self.state != "powerup" or power not in self.power_choices:
            return
        self.powers.add(power)
        data = self.store.data
        if power not in data["unlocked_powers"]:
            data["unlocked_powers"].append(power)
        data["equipped_powers"] = sorted(self.powers)
        data["pending_power_level"] = 0
        if (self.level_index + 1) % 5 == 0 and self.level_index + 1 == data["checkpoint"]:
            data["checkpoint_powers"] = sorted(self.powers)
        self.store.flush()
        self.load_level(self.level_index + 1)

    def update(self, dt, movement=0):
        if self.state != "play":
            self.accumulator = 0
            return
        self.move_input = clamp(movement, -1, 1)
        self.accumulator += max(0, min(dt, .1))
        while self.accumulator >= self.STEP and self.state == "play":
            self.accumulator -= self.STEP
            self.step(self.STEP)

    def step(self, dt):
        self.stats["run_time"] += dt
        self.combat_notice_timer = max(0, self.combat_notice_timer - dt)
        for effect in self.effects:
            effect[3] -= dt
        self.effects = [e for e in self.effects if e[3] > 0]
        if self.hit_freeze > 0:
            self.hit_freeze -= dt
            return
        self.player.move(self.move_input * PLAYER_SPEED * dt, self.bounds)
        if self.intro > 0:
            self.intro = max(0, self.intro - dt)
            return
        self.invulnerability = max(0, self.invulnerability - dt)
        self.cooldown = max(0, self.cooldown - dt)
        self.encounter.update(self, dt)
        if self.state != "play":
            return
        self.update_ai(dt)
        self.update_projectiles(dt)
        if self.state != "play":
            return
        current_balls = self.balls
        for ball in list(current_balls):
            self.update_ball(ball, dt)
            if self.state != "play" or self.balls is not current_balls:
                break

    def update_ai(self, dt):
        if self.encounter.rules().get("objective") == "core":
            return
        for index, paddle in enumerate(self.enemies):
            paddle.stun = max(0, paddle.stun - dt)
            paddle.reaction -= dt
            if paddle.stun > 0:
                continue
            if paddle.reaction <= 0:
                candidates = [b for b in self.balls if b.vx * self.direction > 0 and b.delay <= 0]
                ball = min(candidates, key=lambda b: abs(b.x - paddle.x), default=None)
                if ball:
                    target = predict_y(ball.x, ball.y, ball.vx, ball.vy, paddle.x, self.bounds)
                    paddle.target = target + self.rng.uniform(-self.config["error"], self.config["error"])
                else:
                    paddle.target = self.bounds.centery
                paddle.reaction = self.rng.uniform(.32, .52)
            distance = paddle.target - paddle.y
            if self.config.get("paddles", 1) > 1:
                # Keep independent paddles in distinct territories as members fall.
                span = self.bounds.height / len(self.enemies)
                paddle.target = clamp(paddle.target, self.bounds.top + index * span + 30,
                                      self.bounds.top + (index + 1) * span - 30)
                distance = paddle.target - paddle.y
            if abs(distance) > 10:
                paddle.move(clamp(distance, -self.config["speed"] * dt, self.config["speed"] * dt), self.bounds)

    def update_projectiles(self, dt):
        for projectile in list(self.projectiles):
            projectile.x += projectile.vx * dt
            projectile.y += projectile.vy * dt
            # A narrow white-ball escort prevents a required return and a red dodge
            # demanding opposite positions. It only opens near the player's side.
            incoming = [b for b in self.balls if b.vx * self.direction < 0 and b.delay <= 0]
            protected = any(abs(b.x - self.player.x) < 320 and
                            abs(projectile.y - predict_y(b.x, b.y, b.vx, b.vy, self.player.x, self.bounds)) < self.player.height / 2 + 24
                            for b in incoming)
            if not projectile.reflected and not projectile.blockable and protected and abs(projectile.x - self.player.x) < 340:
                self.impact(projectile.x, projectile.y, GRAY)
                self.stats["projectiles_dodged"] += 1
                self.projectiles.remove(projectile)
                continue
            if not projectile.reflected and circle_rect(projectile.x, projectile.y, projectile.radius, self.player.rect):
                if "REFLECT" in self.powers:
                    projectile.reflected = True
                    projectile.vx = self.direction * 480
                    projectile.x = self.player.x + PADDLE_W + 8 if self.direction == 1 else self.player.x - 8
                    self.stats["projectiles_reflected"] += 1
                    self.callout("REFLECT", CYAN)
                    self.impact(projectile.x, projectile.y, CYAN)
                    continue
                if not projectile.blockable:
                    self.hurt()
                else:
                    self.impact(projectile.x, projectile.y, GOLD)
                self.projectiles.remove(projectile)
                if self.state != "play":
                    return
                continue
            if projectile.reflected:
                if self.encounter.rules().get("objective") == "core" and projectile.x >= ARENA.right - 20:
                    if self.encounter.core_open:
                        self.callout("CORE HIT", CYAN)
                        self.damage_enemy()
                    else:
                        self.callout("ATTACK BROKEN", CYAN)
                        self.encounter.pattern_clock = max(self.encounter.pattern_clock, 3)
                        self.encounter.warning = 0
                        self.encounter.lanes.clear()
                        self.impact(ARENA.right - 10, projectile.y, CYAN)
                    if projectile in self.projectiles:
                        self.projectiles.remove(projectile)
                    continue
                hit = None if self.encounter.rules().get("objective") == "core" else next(
                    (p for p in self.enemies if circle_rect(projectile.x, projectile.y, projectile.radius, p.rect)), None)
                block = next((o for o in self.obstacles if o.hp > 0 and circle_rect(projectile.x, projectile.y, projectile.radius, o.rect)), None)
                if hit or block:
                    if hit:
                        hit.stun = 1.1
                    if block:
                        self.obstacles.remove(block)
                    self.impact(projectile.x, projectile.y, CYAN)
                    self.projectiles.remove(projectile)
                    continue
            if projectile.x < ARENA.left - 20 or projectile.x > ARENA.right + 20:
                if not projectile.reflected:
                    self.stats["projectiles_dodged"] += 1
                self.projectiles.remove(projectile)

    def update_ball(self, ball, dt):
        if ball.delay > 0:
            ball.delay = max(0, ball.delay - dt)
            return
        ball.portal_cooldown = max(0, ball.portal_cooldown - dt)
        ball.hidden = max(0, ball.hidden - dt)
        rules = self.encounter.rules()
        old_x, old_y = ball.x, ball.y
        if rules.get("gravity"):
            ball.vy += 150 * dt
        ball.cap()
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt
        if ball.phase_pending and ball.vx * self.direction < 0:
            crossed_center = old_x >= ARENA.centerx > ball.x if self.direction == 1 else old_x <= ARENA.centerx < ball.x
            if crossed_center:
                ball.phase_pending = False
                ball.hidden = .28
                self.callout("PHASE", VIOLET, .45)
                self.impact(ball.x, ball.y, VIOLET)
        ball.trail.append((ball.x, ball.y))
        ball.trail = ball.trail[-7:]
        if ball.y <= self.bounds.top + BALL_RADIUS:
            self.encounter.wall_bounce(self, ball, True)
        elif ball.y >= self.bounds.bottom - BALL_RADIUS:
            self.encounter.wall_bounce(self, ball, False)

        for obstacle in list(self.obstacles):
            if obstacle.warning > 0 or not circle_rect(ball.x, ball.y, BALL_RADIUS, obstacle.rect):
                continue
            if old_x <= obstacle.rect.left - BALL_RADIUS or old_x >= obstacle.rect.right + BALL_RADIUS:
                ball.vx *= -1
                ball.x = obstacle.rect.left - BALL_RADIUS - .1 if old_x < obstacle.rect.centerx else obstacle.rect.right + BALL_RADIUS + .1
            else:
                ball.vy *= -1
                ball.y = obstacle.rect.top - BALL_RADIUS - .1 if old_y < obstacle.rect.centery else obstacle.rect.bottom + BALL_RADIUS + .1
            if obstacle.hp > 0:
                obstacle.hp -= 2 if ball.charged else 1
                if obstacle.hp <= 0:
                    self.obstacles.remove(obstacle)
            self.impact(ball.x, ball.y, CYAN if ball.charged else WHITE)
            break

        if ball.vx * self.direction < 0 and circle_rect(ball.x, ball.y, BALL_RADIUS, self.player.rect):
            ball.rebound(self.player, self.direction)
            self.rally += 1
            self.return_count += 1
            self.stats["returns"] += 1
            self.stats["longest_rally"] = max(self.stats["longest_rally"], self.rally)
            ball.returned = True
            ball.charged = "SHOCK" in self.powers and self.return_count % 3 == 0
            ball.bank = "RICOCHET" in self.powers
            self.encounter.returned(self, ball, True)
            if ball.charged:
                self.callout("SHOCK CHARGED", CYAN)
            self.impact(ball.x, ball.y, CYAN if ball.charged else WHITE)
            self.hit_freeze = .012 if self.store.data["settings"]["effects"] else 0

        objective = rules.get("objective")
        if ball.vx * self.direction > 0 and objective not in ("core", "survive"):
            for paddle in list(self.enemies):
                if circle_rect(ball.x, ball.y, BALL_RADIUS, paddle.rect):
                    ball.rebound(paddle, -self.direction)
                    self.enemy_returns += 1
                    if ball.charged:
                        paddle.stun = 1.4
                        self.callout("SHOCK: STUN", CYAN)
                    ball.charged = ball.bank = False
                    self.encounter.returned(self, ball, False)
                    self.impact(ball.x, ball.y)
                    self.coordinate_multiball(ball)
                    if objective == "swarm" and ball.returned:
                        self.enemies.remove(paddle)
                        self.damage_enemy()
                    elif objective == "final" and ball.returned:
                        self.damage_enemy()
                    break

        crossed_player = ball.x < ARENA.left - 18 if self.direction == 1 else ball.x > ARENA.right + 18
        crossed_enemy = ball.x > ARENA.right + 18 if self.direction == 1 else ball.x < ARENA.left - 18
        if crossed_player:
            self.hurt(rally_miss=True)
        elif crossed_enemy:
            if objective == "survive":
                ball.vx = -abs(ball.vx)
                ball.x = ARENA.right - BALL_RADIUS
            elif objective == "core":
                if ball.returned and self.encounter.core_open and abs(ball.y - self.bounds.centery) < 110:
                    self.damage_enemy()
                    if self.state == "play" and ball in self.balls:
                        self.serve()
                else:
                    ball.vx = -abs(ball.vx)
                    ball.x = ARENA.right - BALL_RADIUS
            elif objective == "swarm" or (objective == "breakout" and self.obstacles):
                ball.vx *= -1
                ball.x = ARENA.right - BALL_RADIUS
            elif not ball.returned:
                # A free serve establishes the rally; it cannot win the encounter
                # without the player ever touching the ball.
                ball.vx = -self.direction * abs(ball.vx)
                ball.x = ARENA.right - BALL_RADIUS if self.direction == 1 else ARENA.left + BALL_RADIUS
            else:
                damage = 2 if ball.charged and ball.bank else 1
                for _ in range(min(damage, self.enemy_hp)):
                    if self.state == "play":
                        self.damage_enemy()
                if self.state == "play" and ball in self.balls:
                    # Reset only the scored ball; preserve the other rally in multiball.
                    ball.x, ball.y = ARENA.center
                    ball.vx, ball.vy = self.direction * BALL_START_SPEED, self.rng.uniform(-100, 100)
                    ball.delay = .8
                    ball.charged = ball.bank = False
                    ball.returned = False
                    ball.trail.clear()

    def coordinate_multiball(self, ball):
        """Closely timed enemy returns share an intercept; no impossible split saves."""
        others = [b for b in self.balls if b is not ball and b.vx * self.direction < 0 and b.delay <= 0]
        for other in others:
            arrival = abs((ball.x - self.player.x) / ball.vx)
            other_arrival = abs((other.x - self.player.x) / other.vx)
            if abs(arrival - other_arrival) < .65:
                if self.encounter.rules().get("arena") == "portals":
                    span = self.bounds.height - BALL_RADIUS * 2
                    top = self.bounds.top + BALL_RADIUS
                    target = top + (other.y + other.vy * other_arrival - top) % span
                else:
                    target = predict_y(other.x, other.y, other.vx, other.vy, self.player.x, self.bounds)
                ball.vy = (target - ball.y) / max(.1, arrival)
                ball.cap()

    def menu_items(self):
        if self.state == "menu":
            return ["PLAY", "CONTINUE", "STATS", "OPTIONS", "QUIT"]
        if self.state == "pause":
            return ["RESUME", "RESTART CHECKPOINT", "MENU", "QUIT"]
        if self.state in ("defeat", "victory"):
            return ["RESTART CHECKPOINT", "MENU", "QUIT"]
        if self.state == "cleared":
            return ["NEXT LEVEL", "MENU"]
        if self.state == "powerup":
            return self.power_choices
        if self.state == "stats":
            return ["BACK"]
        if self.state == "options":
            data = self.store.data
            return [f"EFFECTS: {'ON' if data['settings']['effects'] else 'OFF'}",
                    f"HIGH CONTRAST: {'ON' if data['settings']['high_contrast'] else 'OFF'}",
                    f"PADDLE: {data['selected_cosmetic']}", "BACK"]
        return []

    def activate(self):
        items = self.menu_items()
        if not items:
            return
        action = items[self.selection % len(items)]
        if self.state == "powerup":
            self.choose_power(action)
        elif action == "PLAY":
            self.start()
        elif action == "CONTINUE":
            self.start("continue")
        elif action == "RESTART CHECKPOINT":
            self.start("checkpoint")
        elif action == "NEXT LEVEL":
            self.load_level(self.level_index + 1)
        elif action == "RESUME":
            self.state = "play"
        elif action in ("MENU", "BACK"):
            self.store.flush()
            self.state = "menu"
            self.selection = 0
        elif action == "QUIT":
            self.store.flush()
            self.state = "quit"
        elif action in ("STATS", "OPTIONS"):
            self.state = action.lower()
            self.selection = 0
        elif action.startswith("EFFECTS"):
            self.store.data["settings"]["effects"] = not self.store.data["settings"]["effects"]
            self.store.flush()
        elif action.startswith("HIGH CONTRAST"):
            self.store.data["settings"]["high_contrast"] = not self.store.data["settings"]["high_contrast"]
            self.store.flush()
        elif action.startswith("PADDLE"):
            data = self.store.data
            choices = data["unlocked_cosmetics"]
            data["selected_cosmetic"] = choices[(choices.index(data["selected_cosmetic"]) + 1) % len(choices)]
            self.store.flush()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.store.flush()
            self.state = "quit"
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            if self.state == "play":
                self.state, self.selection = "pause", 0
                self.store.flush()
            elif self.state == "pause":
                self.state = "play"
            elif self.state in ("stats", "options"):
                self.state, self.selection = "menu", 0
            return
        if self.state == "play":
            if event.key == pygame.K_SPACE:
                self.use_ability()
            return
        items = self.menu_items()
        if items:
            if event.key in (pygame.K_w, pygame.K_UP, pygame.K_LEFT):
                self.selection = (self.selection - 1) % len(items)
            elif event.key in (pygame.K_s, pygame.K_DOWN, pygame.K_RIGHT):
                self.selection = (self.selection + 1) % len(items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.activate()
