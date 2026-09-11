"""Simulation and lifecycle. Rendering lives in ui.py; no display is opened here."""
import math
import random
import pygame
from entities import Ball, Paddle, circle_rect
from encounters import Encounter
from levels import LEVELS, POWER_CHOICES
from save import SaveStore
from campaign import STORY, RELICS, CODEX, ACHIEVEMENTS, daily_seed, dungeon_for, map_nodes
from settings import (ARENA, PLAYER_X, ENEMY_X, PLAYER_SPEED, PADDLE_W,
                      BALL_RADIUS, BALL_START_SPEED, BALL_MAX_SPEED, WHITE, CYAN, RED, GRAY,
                      GOLD, VIOLET, clamp, predict_y)
# Audio is optional – created by main.py and injected via game.audio.
# When None (headless / tests), all audio calls are simply skipped.



class Game:
    STEP = 1 / 120

    def __init__(self, save_path=None, seed=None):
        self.store = SaveStore(save_path)
        self.rng = random.Random(seed)
        self.state = "menu"
        self.selection = 0
        self.accumulator = 0
        self.effects = []
        self.powers = {"BLINK"}
        self.power_choices = []
        self.relic_choices = []
        self.story_lines = ()
        self.story_page = 0
        self.pending_start = None
        self.daily_mode = False
        self.challenge_mode = "CAMPAIGN"
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
        self.chrono_timer = 0.0
        self.chrono_cooldown = 0.0
        self.aegis_shield_ready = True
        self.aegis_timer = 0.0
        self.inferno_banks = 0
        # Injected by main.py; None in tests / headless mode (all calls no-op).
        self.audio = None


    @property
    def config(self):
        return LEVELS[self.level_index]

    @property
    def direction(self):
        reverse = bool(self.config.get("reverse")) ^ (self.challenge_mode == "MIRROR WORLD")
        return -1 if reverse else 1

    @property
    def stats(self):
        return self.store.data["stats"]

    def start(self, mode="new", chosen_level=None):
        data = self.store.data
        max_lvl = len(LEVELS)
        if chosen_level is not None:
            level = max(1, min(max_lvl, chosen_level))
            self.powers = set(data["equipped_powers"]) | {"BLINK"}
        elif mode == "continue":
            level = max(1, min(max_lvl, data["continue_level"]))
            self.powers = set(data["equipped_powers"]) | {"BLINK"}
        elif mode == "checkpoint":
            level = min(max_lvl, data["checkpoint"] + 1)
            self.powers = set(data["checkpoint_powers"]) | {"BLINK"}
        else:
            level = 1
            self.powers = {"BLINK"}
        self.load_level(level - 1)
        pending = data["pending_power_level"]
        if mode in ("continue", "checkpoint") and pending and pending + 1 == level:
            self.load_level(pending - 1)
            self.power_choices = [p for p in POWER_CHOICES[pending] if p not in self.powers]
            self.state = "powerup" if self.power_choices else "cleared"

    def begin_campaign(self):
        """Start through the authored prologue; direct start() remains test/tool friendly."""
        self.pending_start = ("new", None)
        self.open_story(1)

    def start_challenge(self, name):
        self.challenge_mode = name
        self.daily_mode = False
        self.powers = set(self.store.data["unlocked_powers"]) | {"BLINK"}
        if name == "REMIX":
            self.rng.seed(daily_seed() ^ self.store.data["mastery"])
            self.load_level(0)
        elif name == "BOSS RUSH":
            self.load_level(4)
        else:
            self.load_level(0)

    def next_level_index(self):
        step = 5 if self.challenge_mode == "BOSS RUSH" else 1
        return min(len(LEVELS) - 1, self.level_index + step)

    def open_story(self, level):
        self.story_lines = STORY.get(level, ())
        if not self.story_lines:
            mode, chosen = self.pending_start or ("continue", level)
            self.pending_start = None
            self.start(mode, chosen)
            return
        self.story_page = 0
        self.state = "story"
        self.selection = 0
        if level not in self.store.data["seen_story"]:
            self.store.data["seen_story"].append(level)
            self.store.flush()

    def continue_to_level(self, index):
        level = max(1, min(len(LEVELS), index + 1))
        if level in STORY and level not in self.store.data["seen_story"]:
            self.pending_start = ("continue", level)
            self.open_story(level)
        else:
            self.load_level(index)

    def advance_story(self):
        self.story_page += 2
        if self.story_page < len(self.story_lines):
            return
        mode, chosen = self.pending_start or ("continue", 1)
        self.pending_start = None
        self.start(mode, chosen)

    def start_daily(self):
        self.daily_mode = True
        self.rng.seed(daily_seed())
        level = 1 + daily_seed() % len(LEVELS)
        self.start("continue", level)

    def unlock(self, achievement):
        if achievement in ACHIEVEMENTS and achievement not in self.store.data["achievements"]:
            self.store.data["achievements"].append(achievement)
            self.callout(f"ACHIEVEMENT: {achievement}", GOLD, 2.0)


    def load_level(self, index):
        self.level_index = max(0, min(len(LEVELS) - 1, index))
        self.encounter = Encounter(self.config)
        assist = self.store.data["settings"].get("assist", "STANDARD")
        self.encounter.pattern_clock += 1.0 if assist == "GENTLE" else 2.0 if assist == "STORY" else 0.0
        if "QUIET BELL" in self.store.data["relics"]:
            self.encounter.pattern_clock += .6
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
        self.intro = (4.0 if index == 0 else 2.8) + (0.8 if assist == "GENTLE" else 1.5 if assist == "STORY" else 0)
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
        settings = self.store.data["settings"]
        if settings["effects"] and settings.get("intensity", 8) > 0:
            self.effects.append([x, y, color, .18])
            self.effects = self.effects[-max(4, settings.get("intensity", 8) * 3):]

    def callout(self, text, color=WHITE, duration=.8):
        self.combat_notice = text
        self.combat_notice_color = color
        self.combat_notice_timer = duration

    def use_ability(self):
        if self.state != "play" or "BLINK" not in self.powers or self.cooldown > 0 or self.intro > 0:
            return
        # Blink ignores phantom decoy balls – only intercept real incoming balls.
        incoming = [b for b in self.balls
                    if b.vx * self.direction < 0 and b.delay <= 0 and not b.decoy]
        target = min(incoming, key=lambda b: abs(b.x - self.player.x), default=None)
        if target is None:
            self.callout("BLINK NEEDS AN INCOMING BALL", GRAY)
            return
        old_y = self.player.y
        intercept = self.predict_intercept(target, self.player.x)
        self.player.move(clamp(intercept - self.player.y, -210, 210), self.bounds)
        self.cooldown = 3.6
        self.invulnerability = max(self.invulnerability, .45)
        self.stats["abilities_used"] += 1
        self.callout("BLINK", CYAN)
        self.impact(self.player.x, old_y, CYAN)
        self.impact(self.player.x, self.player.y, CYAN)
        if self.audio:
            self.audio.paddle_hit()

    def use_chrono(self):
        if self.state != "play" or "CHRONO" not in self.powers or self.chrono_cooldown > 0 or self.intro > 0:
            return
        self.chrono_timer = 2.5
        self.chrono_cooldown = 7.0
        self.stats["abilities_used"] += 1
        self.callout("CHRONO WARP!", CYAN, 1.0)
        self.impact(self.player.x, self.player.y, CYAN)
        if self.audio:
            self.audio.phantom_phase()

    def hurt(self, rally_miss=False):
        if self.state != "play":
            return
        if "AEGIS" in self.powers and self.aegis_shield_ready:
            self.aegis_shield_ready = False
            self.aegis_timer = 18.0
            self.invulnerability = 1.2
            self.callout("AEGIS BARRIER ABSORB!", GOLD, 1.2)
            self.impact(self.player.x, self.player.y, GOLD)
            if self.audio:
                self.audio.bullet_reflect()
            if rally_miss:
                for b in self.balls:
                    if (b.x < self.player.x if self.direction == 1 else b.x > self.player.x):
                        b.vx = abs(b.vx) * self.direction
                        b.x = self.player.x + (PADDLE_W + BALL_RADIUS + 10) * self.direction
                        b.portal_cooldown = 0.2
            return
        if self.invulnerability <= 0:
            self.player_hp -= 1
            self.level_damage += 1
            self.stats["damage_taken"] += 1
            self.invulnerability = 1.5
            self.impact(self.player.x, self.player.y, RED)
            if self.audio:
                self.audio.player_hurt()
            if self.player_hp <= 0:
                self.state = "defeat"
                self.selection = 0
                self.stats["deaths"] += 1
                self.stats["losses"] += 1
                self.store.data["continue_level"] = min(len(LEVELS), self.store.data["checkpoint"] + 1)
                self.store.data["equipped_powers"] = sorted(self.store.data["checkpoint_powers"])
                self.store.data["pending_power_level"] = 0
                self.store.flush()
        if rally_miss and self.state == "play":
            self.rally = 0
            self.projectiles.clear()
            self.encounter.warning = 0
            self.encounter.lanes.clear()
            self.encounter.fan.clear()
            self.encounter.pattern_clock = 3.5
            # Also remove any lingering decoy balls when the rally resets.
            self.balls = [b for b in self.balls if not b.decoy]
            self.serve()

    def damage_enemy(self):
        if self.state != "play":
            return
        self.enemy_hp -= 1
        self.impact(ENEMY_X if self.direction == 1 else PLAYER_X, self.bounds.centery)
        if self.audio:
            self.audio.enemy_hurt()
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
            self.unlock("UNTOUCHABLE")
        data["mastery"] += (3 if "MERCY GLASS" in data["relics"] else 2) if self.level_damage == 0 else 1
        if level % 5 == 0 and self.level_damage == 0:
            data["rescued_memories"] = min(25, data["rescued_memories"] + 1)
        self.unlock("BONE BROKEN" if level == 25 else "KEEPER" if level == 101 else
                    "CHANGE THE LOOP" if level == 125 else "")
        codex_unlock = {1: "THE SILT ARCADE", 25: "THE RETURN", 75: "THE MISSING NOTE", 125: "THE ARCHITECT"}.get(level)
        if codex_unlock and codex_unlock not in data["codex"]:
            data["codex"].append(codex_unlock)
        if level % 5 == 0:
            available = [r for r in RELICS if r not in data["relics"]]
            self.relic_choices = available[:3]
        data["highest_level"] = max(data["highest_level"], min(len(LEVELS), level + 1))
        data["continue_level"] = min(len(LEVELS), level + 1)
        data["equipped_powers"] = sorted(self.powers)
        if level % 5 == 0:
            self.stats["bosses_defeated"] += 1
            if level >= data["checkpoint"]:
                data["checkpoint"] = level
                data["checkpoint_powers"] = sorted(self.powers)
            cosmetic = {5: "OUTLINE", 10: "NOTCHED", 15: "CATHEDRAL", 20: "PHOSPHOR"}.get(self.config.get("room"), "SOLID")
            if cosmetic not in data["unlocked_cosmetics"]:
                data["unlocked_cosmetics"].append(cosmetic)
        self.power_choices = [p for p in POWER_CHOICES.get(level, ()) if p not in self.powers]
        data["pending_power_level"] = level if self.power_choices else 0
        if level == len(LEVELS):
            data["completed"] = True
            data["ending"] = "RETURN" if data["rescued_memories"] >= 15 else "BREAK" if data["rescued_memories"] >= 5 else "LOOP"
            if self.challenge_mode in ("MIRROR WORLD", "BOSS RUSH", "REMIX") and self.challenge_mode not in data["completed_challenges"]:
                data["completed_challenges"].append(self.challenge_mode)
            self.state = "victory"
        elif self.config.get("category") == "ELITE" and [r for r in RELICS if r not in data["relics"]]:
            self.relic_choices = [r for r in RELICS if r not in data["relics"]][:3]
            self.state = "relic"
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
        self.continue_to_level(self.next_level_index())

    def choose_relic(self, relic):
        if self.state != "relic" or relic not in self.relic_choices:
            return
        if relic not in self.store.data["relics"]:
            self.store.data["relics"].append(relic)
        self.store.flush()
        self.continue_to_level(self.next_level_index())

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
        if self.player.stun > 0:
            self.player.stun = max(0.0, self.player.stun - dt)
        else:
            self.player.move(self.move_input * PLAYER_SPEED * dt, self.bounds)
        if self.intro > 0:
            self.intro = max(0, self.intro - dt)
            return

        self.invulnerability = max(0, self.invulnerability - dt)
        self.cooldown = max(0, self.cooldown - dt)

        # Chrono time dilation & cooldown
        if self.chrono_cooldown > 0:
            self.chrono_cooldown = max(0.0, self.chrono_cooldown - dt)
        sim_dt = dt
        if self.chrono_timer > 0:
            self.chrono_timer = max(0.0, self.chrono_timer - dt)
            sim_dt = dt * 0.35

        # Aegis shield recharge
        if not self.aegis_shield_ready:
            self.aegis_timer = max(0.0, self.aegis_timer - dt)
            if self.aegis_timer <= 0:
                self.aegis_shield_ready = True
                self.callout("AEGIS SHIELD READY", GOLD, 0.8)

        self.encounter.update(self, sim_dt)
        if self.state != "play":
            return
        self.update_ai(sim_dt)
        self.update_projectiles(sim_dt)
        if self.state != "play":
            return
        current_balls = self.balls
        for ball in list(current_balls):
            self.update_ball(ball, sim_dt)
            if self.state != "play" or self.balls is not current_balls:
                break

    def update_ai(self, dt):
        if self.encounter.rules().get("objective") == "core":
            return
        candidates = [b for b in self.balls
                      if b.vx * self.direction > 0 and b.delay <= 0 and not b.decoy]
        num_enemies = len(self.enemies)

        for index, paddle in enumerate(self.enemies):
            paddle.stun = max(0, paddle.stun - dt)
            paddle.reaction -= dt
            if paddle.stun > 0:
                continue
            if paddle.reaction <= 0:
                # Twins Coordinated Intercept:
                if num_enemies == 2:
                    if len(candidates) >= 2:
                        # Dual balls: top twin tracks upper ball, bottom twin tracks lower ball!
                        sorted_balls = sorted(candidates, key=lambda b: b.y)
                        ball = sorted_balls[0] if index == 0 else sorted_balls[-1]
                    elif len(candidates) == 1:
                        ball = candidates[0]
                        pred = self.predict_intercept(ball, paddle.x)
                        # The twin whose natural territory contains the predicted intercept acts as primary;
                        # the sibling covers the rebound zone!
                        if (pred <= self.bounds.centery and index == 0) or (pred > self.bounds.centery and index == 1):
                            target = pred
                            paddle.target = target + self.rng.uniform(-self.config["error"] * 0.5, self.config["error"] * 0.5)
                        else:
                            # Cover wall bank rebound
                            rebound_y = self.bounds.centery + (80 if index == 1 else -80)
                            paddle.target = rebound_y
                        paddle.reaction = self.rng.uniform(.32, .48)
                        ball = None
                    else:
                        ball = None
                else:
                    ball = min(candidates, key=lambda b: abs(b.x - paddle.x), default=None)

                if ball:
                    target = self.predict_intercept(ball, paddle.x)
                    paddle.target = target + self.rng.uniform(-self.config["error"], self.config["error"])
                elif num_enemies != 2 or not candidates:
                    paddle.target = self.bounds.centery
                paddle.reaction = self.rng.uniform(.35, .55)

            # Wraith: if a teleport is imminent, pre-position toward the destination
            if (self.encounter.teleport_warning > 0
                    and self.encounter.teleport_warning < 0.5
                    and index == 0):
                paddle.target = self.encounter.teleport_y

            distance = paddle.target - paddle.y
            if num_enemies == 2:
                # Generous overlapping zones with zero dead center:
                if index == 0:
                    paddle.target = clamp(paddle.target, self.bounds.top + 30, self.bounds.centery + 70)
                else:
                    paddle.target = clamp(paddle.target, self.bounds.centery - 70, self.bounds.bottom - 30)
                distance = paddle.target - paddle.y
            elif num_enemies > 2:
                span = self.bounds.height / num_enemies
                paddle.target = clamp(paddle.target, self.bounds.top + index * span + 30,
                                      self.bounds.top + (index + 1) * span - 30)
                distance = paddle.target - paddle.y

            if abs(distance) > 8:
                paddle.move(clamp(distance, -self.config["speed"] * dt, self.config["speed"] * dt), self.bounds)

    def predict_intercept(self, ball, target_x):
        """Follow current portals, gravity, and obstacles without removing AI error."""
        x, y, vx, vy = ball.x, ball.y, ball.vx, ball.vy
        rules = self.encounter.rules()
        obstacles = [(obstacle.rect.copy(), obstacle.one_sided, obstacle.is_warp_rift) for obstacle in self.obstacles]
        step = 1 / 120
        sim_portal_cooldown = 0.0
        for _ in range(120 * 4):
            sim_portal_cooldown = max(0.0, sim_portal_cooldown - step)
            old_x, old_y = x, y
            if rules.get("gravity"):
                vy += 150 * step
            speed = math.hypot(vx, vy)
            if speed > 700:
                vx, vy = vx * 700 / speed, vy * 700 / speed
            x, y = x + vx * step, y + vy * step
            if y <= self.bounds.top + BALL_RADIUS or y >= self.bounds.bottom - BALL_RADIUS:
                if rules.get("arena") == "portals":
                    y = self.bounds.bottom - BALL_RADIUS if y <= self.bounds.top + BALL_RADIUS else self.bounds.top + BALL_RADIUS
                else:
                    y = clamp(y, self.bounds.top + BALL_RADIUS, self.bounds.bottom - BALL_RADIUS)
                    vy *= -1
            for rect, one_sided, is_warp in obstacles:
                if not circle_rect(x, y, BALL_RADIUS, rect):
                    continue
                if is_warp:
                    if sim_portal_cooldown <= 0:
                        other_rifts = [r for r, _, w in obstacles if w and r != rect]
                        if other_rifts:
                            other_rect = other_rifts[0]
                            exit_dir = 1 if vx > 0 else -1
                            x = other_rect.centerx + exit_dir * (other_rect.width / 2 + BALL_RADIUS + 10)
                            entry_ratio = (y - rect.centery) / max(1, rect.height / 2)
                            y = clamp(other_rect.centery + entry_ratio * (other_rect.height / 2),
                                      self.bounds.top + BALL_RADIUS + 10, self.bounds.bottom - BALL_RADIUS - 10)
                            vy = -vy * 1.05 if abs(vy) > 30 else (120 if y < self.bounds.centery else -120)
                            sim_portal_cooldown = 0.45
                    break
                # One-sided wall: shots moving left (enemy to player) pass straight through!
                if one_sided and vx * self.direction < 0:
                    continue
                if old_x <= rect.left - BALL_RADIUS or old_x >= rect.right + BALL_RADIUS:
                    vx *= -1
                    x = rect.left - BALL_RADIUS if old_x < rect.centerx else rect.right + BALL_RADIUS
                else:
                    vy *= -1
                    y = rect.top - BALL_RADIUS if old_y < rect.centery else rect.bottom + BALL_RADIUS
                break
            crossed = old_x <= target_x <= x if vx > 0 else old_x >= target_x >= x
            if crossed:
                return clamp(y, self.bounds.top + BALL_RADIUS, self.bounds.bottom - BALL_RADIUS)
        return self.bounds.centery


    def update_projectiles(self, dt):
        for projectile in list(self.projectiles):
            projectile.x += projectile.vx * dt
            projectile.y += projectile.vy * dt
            # A narrow white-ball escort prevents a required return and a red dodge
            # demanding opposite positions. It only opens near the player's side.
            incoming = [b for b in self.balls if b.vx * self.direction < 0 and b.delay <= 0]
            protected = any(abs(b.x - self.player.x) < 320 and
                            abs(projectile.y - self.predict_intercept(b, self.player.x)) < self.player.height / 2 + 24
                            for b in incoming)
            if not projectile.reflected and not projectile.blockable and protected and abs(projectile.x - self.player.x) < 340:
                self.impact(projectile.x, projectile.y, GRAY)
                self.stats["projectiles_dodged"] += 1
                self.projectiles.remove(projectile)
                continue
            if not projectile.reflected and circle_rect(projectile.x, projectile.y, projectile.radius, self.player.rect):
                can_reflect = "REFLECT" in self.powers and (self.rng.random() < 0.5)
                if can_reflect:
                    projectile.reflected = True
                    projectile.vx = self.direction * 520
                    projectile.x = self.player.x + PADDLE_W + 8 if self.direction == 1 else self.player.x - 8
                    self.stats["projectiles_reflected"] += 1
                    self.callout("REFLECT!", CYAN)
                    self.impact(projectile.x, projectile.y, CYAN)
                    if projectile.blockable or projectile.arrow:
                        self.encounter.arrow_reflected(self)
                    if self.audio:
                        self.audio.laser_fire()
                    continue

                # Not reflected (failed 50% check or power not equipped):
                if projectile.hunter_bolt:
                    # Hunter sniper bolt: guaranteed 1 tick of damage!
                    self.callout("SNIPED!", RED)
                    self.hurt()
                    if self.audio:
                        self.audio.player_hurt()
                elif projectile.arrow:
                    # Arrows: 50% chance stun, 50% chance 1 tick of damage
                    if self.rng.random() < 0.5:
                        self.player.stun = 0.85
                        self.callout("ARROW STUN!", GOLD)
                        self.impact(self.player.x, self.player.y, GOLD)
                        if self.audio:
                            self.audio.shock_stun()
                    else:
                        self.hurt()
                        if self.audio:
                            self.audio.player_hurt()
                    self.encounter.arrow_reflected(self)
                elif projectile.lightning:
                    # Zeus lightning: damage + electric stun
                    self.player.stun = 0.6
                    self.callout("SHOCKED!", CYAN)
                    self.hurt()
                    if self.audio:
                        self.audio.shock_stun()
                elif projectile.blood_orb:
                    # Vampire King: damage + life leech
                    self.callout("LIFE DRAINED!", RED)
                    self.hurt()
                    if game_rules := self.encounter.rules():
                        self.enemy_hp = min(game_rules.get("hp", 3), self.enemy_hp + 1)
                    if self.audio:
                        self.audio.player_hurt()
                elif not projectile.blockable:
                    self.hurt()
                    if self.audio:
                        self.audio.player_hurt()
                else:
                    # Generic blockable projectile: absorbed by paddle
                    self.impact(projectile.x, projectile.y, GOLD)
                    self.encounter.arrow_reflected(self)

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

        # Stasis suspension (Dream Eater / Alien / Nirvana)
        if ball.stasis_timer > 0:
            ball.stasis_timer = max(0.0, ball.stasis_timer - dt)
            if ball.stasis_timer <= 0:
                ball.vx, ball.vy = ball.stasis_vx, ball.stasis_vy
                ball.cap()
                self.impact(ball.x, ball.y, VIOLET)
                self.callout("STASIS SNAP!", VIOLET, 0.4)
            else:
                ball.x += self.rng.uniform(-0.8, 0.8)
                ball.y += self.rng.uniform(-0.8, 0.8)
                return

        # Telekinesis: actively curve the ball's trajectory mid-air
        if "TELEKINESIS" in self.powers and self.move_input != 0 and ball.vx * self.direction > 0:
            ball.vy = clamp(ball.vy + self.move_input * 220 * dt, -BALL_MAX_SPEED, BALL_MAX_SPEED)

        # Fireball duration & projectile vaporizing
        if ball.fireball:
            ball.fireball_timer = max(0.0, ball.fireball_timer - dt)
            if ball.fireball_timer <= 0:
                ball.fireball = False
            else:
                for p in list(self.projectiles):
                    if not p.reflected and circle_rect(p.x, p.y, p.radius + 6, pygame.Rect(ball.x - 12, ball.y - 12, 24, 24)):
                        self.impact(p.x, p.y, (255, 120, 20))
                        self.projectiles.remove(p)

        if rules.get("gravity"):
            ball.vy += 150 * dt
        ball.cap()
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt

        # Phase-pending: ball fades at midcourt and optionally spawns wraith decoys.
        if ball.phase_pending and ball.vx * self.direction < 0:
            crossed_center = (old_x >= ARENA.centerx > ball.x if self.direction == 1
                              else old_x <= ARENA.centerx < ball.x)
            if crossed_center:
                ball.phase_pending = False
                ball.hidden = ball.hidden_total = .62
                self.callout("PHASE", VIOLET, .45)
                self.impact(ball.x, ball.y, VIOLET)
                if self.audio:
                    self.audio.phantom_phase()
                # Spawn wraith decoys only for real balls (not recursive on decoys).
                if not ball.decoy:
                    self.encounter.maybe_spawn_decoys(self, ball)

        ball.trail.append((ball.x, ball.y))
        ball.trail = ball.trail[-7:]

        # Wall bounces
        if ball.y <= self.bounds.top + BALL_RADIUS:
            self.encounter.wall_bounce(self, ball, True)
            if self.audio and not ball.decoy:
                self.audio.wall_bounce()
        elif ball.y >= self.bounds.bottom - BALL_RADIUS:
            self.encounter.wall_bounce(self, ball, False)
            if self.audio and not ball.decoy:
                self.audio.wall_bounce()

        # Obstacle collisions (acid puddles are indestructible; skip hp deduction)
        for obstacle in list(self.obstacles):
            if obstacle.warning > 0 or not circle_rect(ball.x, ball.y, BALL_RADIUS, obstacle.rect):
                continue
            # Gatekeeper Warp Rift teleport:
            if obstacle.is_warp_rift:
                if ball.portal_cooldown <= 0:
                    other_rifts = [o for o in self.obstacles if o.is_warp_rift and o != obstacle]
                    if other_rifts:
                        other = other_rifts[0]
                        exit_dir = 1 if ball.vx > 0 else -1
                        ball.x = other.rect.centerx + exit_dir * (other.rect.width / 2 + BALL_RADIUS + 10)
                        entry_ratio = (ball.y - obstacle.rect.centery) / max(1, obstacle.rect.height / 2)
                        ball.y = clamp(other.rect.centery + entry_ratio * (other.rect.height / 2),
                                       self.bounds.top + BALL_RADIUS + 10, self.bounds.bottom - BALL_RADIUS - 10)
                        ball.vy = clamp(-ball.vy * 1.05 if abs(ball.vy) > 30 else (120 if ball.y < self.bounds.centery else -120),
                                        -BALL_MAX_SPEED, BALL_MAX_SPEED)
                        ball.portal_cooldown = 0.45
                        ball.trail.clear()
                        self.impact(obstacle.rect.centerx, obstacle.rect.centery, CYAN)
                        self.impact(ball.x, ball.y, VIOLET)
                        self.callout("WARP TRANSIT!", CYAN, 0.45)
                        if self.audio:
                            self.audio.phantom_phase()
                continue

            # Ethereal/energy fields pass-through without solid brick bounce:
            if obstacle.is_tractor_beam or obstacle.is_whirlpool or obstacle.is_mandala:
                continue

            # Alien defense drone hit
            if obstacle.is_drone:
                if obstacle in self.obstacles:
                    self.obstacles.remove(obstacle)
                self.impact(obstacle.rect.centerx, obstacle.rect.centery, CYAN)
                self.callout("DRONE DESTROYED!", CYAN, 0.5)
                for vy_off in (-90, 90):
                    self.projectiles.append(Projectile(obstacle.rect.centerx, obstacle.rect.centery, -self.direction * 350, vy=vy_off, blockable=False, radius=6))
                if self.audio:
                    self.audio.laser_fire()
                ball.vx *= -1
                continue

            # One-sided wall (The Mason): enemy shots moving toward player pass straight through!
            if obstacle.one_sided and ball.vx * self.direction < 0:
                continue

            if old_x <= obstacle.rect.left - BALL_RADIUS or old_x >= obstacle.rect.right + BALL_RADIUS:
                ball.vx *= -1
                ball.x = (obstacle.rect.left - BALL_RADIUS - .1
                          if old_x < obstacle.rect.centerx
                          else obstacle.rect.right + BALL_RADIUS + .1)
            else:
                ball.vy *= -1
                ball.y = (obstacle.rect.top - BALL_RADIUS - .1
                          if old_y < obstacle.rect.centery
                          else obstacle.rect.bottom + BALL_RADIUS + .1)

            if obstacle.one_sided and not obstacle.is_bone_spire:
                # The Mason's wall: impart a kinetic shock rebound!
                ball.vx *= 1.15
                ball.cap()
                self.callout("MASON SLAM!", WHITE, 0.4)
                if self.audio:
                    self.audio.wall_bounce()
            elif obstacle.is_bone_spire:
                self.callout("BONE SHATTER!", VIOLET, 0.35)

            # Indestructible obstacles (hp <= 0): just deflect, no hp change.
            if obstacle.hp > 0:
                if ball.fireball:
                    obstacle.hp = 0
                    self.callout("INFERNO CRUSH!", (255, 120, 20), 0.45)
                else:
                    obstacle.hp -= 2 if ball.charged else 1
                if obstacle.hp <= 0:
                    self.obstacles.remove(obstacle)
                    self.encounter.obstacle_destroyed(self, obstacle)
            self.impact(ball.x, ball.y, VIOLET if obstacle.is_bone_spire else (CYAN if ball.charged else WHITE))
            break


        # Player paddle contact
        if ball.vx * self.direction < 0 and circle_rect(ball.x, ball.y, BALL_RADIUS, self.player.rect):
            if ball.decoy:
                # Decoy pops into shadow smoke, 0 damage, brief static glitch
                self.impact(ball.x, ball.y, VIOLET)
                self.callout("PHANTOM POP!", VIOLET, 0.4)
                self.player.stun = 0.18
                if ball in self.balls:
                    self.balls.remove(ball)
                if self.audio:
                    self.audio.phantom_phase()
                return

            ball.rebound(self.player, self.direction)
            self.rally += 1
            self.return_count += 1
            self.stats["returns"] += 1
            self.unlock("FIRST RETURN")
            if "HUNTER'S MARK" in self.store.data["relics"] and abs(ball.y - self.player.y) <= self.player.height * .16:
                ball.relic_marked = True
                self.callout("HUNTER'S MARK", GOLD, .55)
            if "BANKED OATH" in self.store.data["relics"] and ball.relic_banked:
                self.impact(ball.x, ball.y, GOLD)
                self.callout("BANKED OATH", GOLD, .55)
                ball.relic_banked = False
            self.stats["longest_rally"] = max(self.stats["longest_rally"], self.rally)
            ball.returned = True
            ball.charged = "SHOCK" in self.powers and self.return_count % 3 == 0
            ball.bank = "RICOCHET" in self.powers
            if "INFERNO" in self.powers and ball.bank:
                ball.fireball = True
                ball.fireball_timer = 3.5
                self.callout("INFERNO FIREBALL!", (255, 100, 20), 0.7)
                if self.audio:
                    self.audio.laser_fire()
            self.encounter.returned(self, ball, True)
            if ball.charged:
                self.callout("SHOCK CHARGED", CYAN)
                if self.audio:
                    self.audio.shock_stun()
            self.impact(ball.x, ball.y, CYAN if ball.charged else WHITE)
            self.hit_freeze = .012 if self.store.data["settings"]["effects"] else 0
            if self.audio:
                self.audio.paddle_hit()

        objective = rules.get("objective")
        if ball.vx * self.direction > 0 and objective not in ("core", "survive"):
            for paddle in list(self.enemies):
                if circle_rect(ball.x, ball.y, BALL_RADIUS, paddle.rect):
                    ball.rebound(paddle, -self.direction)
                    ball.relic_marked = False
                    self.enemy_returns += 1
                    if ball.fireball:
                        self.callout("INFERNO SLAM!", (255, 80, 20), 0.8)
                        self.damage_enemy()
                        ball.fireball = False
                    if ball.charged:
                        paddle.stun = 1.4
                        self.callout("SHOCK: STUN", CYAN)
                        if self.audio:
                            self.audio.shock_stun()
                    ball.charged = ball.bank = False
                    self.encounter.returned(self, ball, False)
                    self.impact(ball.x, ball.y)
                    if self.audio:
                        self.audio.paddle_hit()
                    self.coordinate_multiball(ball)
                    if objective == "swarm" and ball.returned:
                        self.encounter.swarm_paddle_destroyed(self, paddle)
                        self.enemies.remove(paddle)
                        self.damage_enemy()
                    elif objective == "final" and ball.returned:
                        self.damage_enemy()
                    break


        crossed_player = ball.x < ARENA.left - 18 if self.direction == 1 else ball.x > ARENA.right + 18
        crossed_enemy = ball.x > ARENA.right + 18 if self.direction == 1 else ball.x < ARENA.left - 18
        if crossed_player:
            if ball.decoy:
                # Decoy crossing the player goal line: dissolve silently, no HP loss.
                if ball in self.balls:
                    self.balls.remove(ball)
                return
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
                damage = (2 if ball.charged and ball.bank else 1) + (1 if ball.fireball else 0)
                for _ in range(min(damage, self.enemy_hp)):
                    if self.state == "play":
                        self.damage_enemy()
                if self.state == "play" and ball in self.balls:
                    # Reset only the scored ball; preserve the other rally in multiball.
                    ball.x, ball.y = ARENA.center
                    ball.vx, ball.vy = self.direction * BALL_START_SPEED, self.rng.uniform(-100, 100)
                    ball.delay = .8
                    ball.charged = ball.bank = ball.fireball = False
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
            items = ["PLAY", "CONTINUE", "STATS", "OPTIONS", "DUNGEON MAP", "CODEX", "DAILY CHALLENGE"]
            if self.store.data["completed"]:
                items += ["REMIX", "MIRROR WORLD", "BOSS RUSH"]
            return items + ["QUIT"]
        if self.state in ("map", "codex", "story"):
            return [] if self.state == "story" else ["BACK"]
        if self.state == "continue":
            highest = max(1, min(len(LEVELS), self.store.data.get("highest_level", 1)))
            items = []
            for lvl in range(1, highest + 1):
                if lvl not in (1, highest) and lvl % 5 != 0:
                    continue
                name = LEVELS[lvl - 1]["name"]
                items.append(f"LEVEL {lvl:02d}: {name}")
            items.append("BACK")
            return items
        if self.state == "pause":
            return ["RESUME", "RESTART CHECKPOINT", "MENU", "QUIT"]
        if self.state in ("defeat", "victory"):
            return ["RESTART CHECKPOINT", "MENU", "QUIT"]
        if self.state == "cleared":
            return ["NEXT LEVEL", "MENU"]
        if self.state == "powerup":
            return self.power_choices
        if self.state == "relic":
            return self.relic_choices
        if self.state == "stats":
            return ["BACK"]
        if self.state == "options":
            data = self.store.data
            return [f"EFFECTS: {'ON' if data['settings']['effects'] else 'OFF'}",
                    f"HIGH CONTRAST: {'ON' if data['settings']['high_contrast'] else 'OFF'}",
                    f"SOUND: {'ON' if data['settings'].get('sound', True) else 'OFF'}",
                    f"PRESENTATION: {data['settings']['presentation']}",
                    f"REDUCED FLASH: {'ON' if data['settings']['reduced_flash'] else 'OFF'}",
                    f"ASSIST: {data['settings']['assist']}",
                    f"MUSIC: {data['settings']['music_volume'] * 10}%",
                    f"SFX: {data['settings']['sfx_volume'] * 10}%",
                    f"INTENSITY: {data['settings']['intensity'] * 10}%",
                    f"SCREEN SHAKE: {data['settings']['screen_shake'] * 10}%",
                    f"UI SCALE: {data['settings']['ui_scale'] * 10}%",
                    f"PADDLE: {data['selected_cosmetic']}", "BACK"]

        return []

    def activate(self):
        items = self.menu_items()
        if not items:
            return
        action = items[self.selection % len(items)]
        if self.state == "powerup":
            self.choose_power(action)
        elif self.state == "relic":
            self.choose_relic(action)
        elif action == "PLAY":
            self.begin_campaign()
        elif action == "CONTINUE":
            self.state = "continue"
            highest = max(1, self.store.data.get("highest_level", 1))
            cont = self.store.data.get("continue_level", 1)
            self.selection = min(highest - 1, max(0, cont - 1))
        elif action.startswith("LEVEL "):
            lvl_str = action.split(":")[0].replace("LEVEL", "").strip()
            chosen = int(lvl_str)
            self.start(mode="continue", chosen_level=chosen)
        elif action == "RESTART CHECKPOINT":
            self.start("checkpoint")
        elif action == "NEXT LEVEL":
            self.continue_to_level(self.next_level_index())
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
        elif action == "DUNGEON MAP":
            self.state, self.selection = "map", 0
        elif action == "CODEX":
            self.state, self.selection = "codex", 0
        elif action == "DAILY CHALLENGE":
            self.start_daily()
        elif action in ("REMIX", "MIRROR WORLD", "BOSS RUSH"):
            self.start_challenge(action)
        elif action.startswith("EFFECTS"):
            self.store.data["settings"]["effects"] = not self.store.data["settings"]["effects"]
            self.store.flush()
        elif action.startswith("HIGH CONTRAST"):
            self.store.data["settings"]["high_contrast"] = not self.store.data["settings"]["high_contrast"]
            self.store.flush()
        elif action.startswith("SOUND"):
            current = self.store.data["settings"].get("sound", True)
            self.store.data["settings"]["sound"] = not current
            if self.audio:
                self.audio.set_enabled(not current)
            self.store.flush()
        elif action.startswith("PRESENTATION"):
            settings = self.store.data["settings"]
            settings["presentation"] = "CLASSIC" if settings["presentation"] == "CATHEDRAL" else "CATHEDRAL"
            self.store.flush()
        elif action.startswith("REDUCED FLASH"):
            settings = self.store.data["settings"]
            settings["reduced_flash"] = not settings["reduced_flash"]
            self.store.flush()
        elif action.startswith("ASSIST"):
            settings = self.store.data["settings"]
            choices = ("STANDARD", "GENTLE", "STORY")
            settings["assist"] = choices[(choices.index(settings["assist"]) + 1) % len(choices)]
            self.store.flush()
        elif any(action.startswith(prefix) for prefix in ("MUSIC", "SFX", "INTENSITY", "SCREEN SHAKE", "UI SCALE")):
            key = next(k for prefix, k in (("MUSIC", "music_volume"), ("SFX", "sfx_volume"),
                       ("INTENSITY", "intensity"), ("SCREEN SHAKE", "screen_shake"), ("UI SCALE", "ui_scale"))
                       if action.startswith(prefix))
            settings = self.store.data["settings"]
            settings[key] = (settings[key] + 1) % 11
            if self.audio and key == "music_volume":
                self.audio.set_music_volume(settings[key] / 35)
            elif self.audio and key == "sfx_volume":
                self.audio.set_sfx_volume(settings[key] / 10)
            self.store.flush()
        elif action.startswith("PADDLE"):
            data = self.store.data
            choices = data["unlocked_cosmetics"]
            data["selected_cosmetic"] = choices[(choices.index(data["selected_cosmetic"]) + 1) % len(choices)]
            self.store.flush()
        if self.audio:
            self.audio.menu_click()


    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.store.flush()
            self.state = "quit"
        if event.type == pygame.MOUSEBUTTONDOWN and self.state == "play":
            if event.button == 3:  # Right-click triggers Chrono
                self.use_chrono()
        if event.type == pygame.JOYBUTTONDOWN:
            if self.state == "play" and event.button == 0:
                self.use_ability()
            elif self.state == "play" and event.button == 1:
                self.use_chrono()
            elif event.button in (7, 9):
                if self.state == "play":
                    self.state, self.selection = "pause", 0
                elif self.state == "pause":
                    self.state = "play"
            elif self.state != "play" and event.button == 0:
                if self.state == "story":
                    self.advance_story()
                else:
                    self.activate()
            return
        if event.type == pygame.JOYHATMOTION and self.state != "play":
            items = self.menu_items()
            if items and event.value[1]:
                self.selection = (self.selection - event.value[1]) % len(items)
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            if self.state == "play":
                self.state, self.selection = "pause", 0
                self.store.flush()
            elif self.state == "pause":
                self.state = "play"
            elif self.state in ("stats", "options", "continue", "map", "codex", "story"):
                self.state, self.selection = "menu", 0
            return
        if self.state == "story":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.advance_story()
            return
        if self.state == "play":
            if event.key == pygame.K_SPACE:
                self.use_ability()
            elif event.key in (pygame.K_e, pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.use_chrono()
            return
        items = self.menu_items()
        if items:
            if event.key in (pygame.K_w, pygame.K_UP):
                self.selection = (self.selection - 1) % len(items)
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                self.selection = (self.selection + 1) % len(items)
            elif event.key == pygame.K_LEFT:
                if self.state == "continue" and len(items) > 7:
                    half = (len(items) - 1 + 1) // 2
                    self.selection = max(0, self.selection - half)
                else:
                    self.selection = (self.selection - 1) % len(items)
            elif event.key == pygame.K_RIGHT:
                if self.state == "continue" and len(items) > 7:
                    half = (len(items) - 1 + 1) // 2
                    self.selection = min(len(items) - 1, self.selection + half)
                else:
                    self.selection = (self.selection + 1) % len(items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.activate()
