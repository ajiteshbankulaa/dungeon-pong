"""A handful of composed rules and four explicit boss scripts, not a generic engine."""
import math
import pygame
from entities import Obstacle, Projectile
from settings import ARENA, PLAYER_X, ENEMY_X, PADDLE_W, BALL_RADIUS, GOLD, VIOLET


class Encounter:
    def __init__(self, config):
        self.config = config
        self.phase = 1
        self.elapsed = 0.0
        self.pattern_clock = 3.0
        self.warning = 0.0
        self.lanes = []
        self.pattern_count = 0
        self.guard = 0.0
        self.guard_waiting_for_return = False
        self.player_shots = 0
        self.enemy_shots = 0
        self.arrow_charge = 0.0
        self.arrow_target = ARENA.centery
        self.teleport_warning = 0.0
        self.teleport_y = ARENA.centery
        self.teleport_cooldown = 5.0
        self.core_open = True

    def rules(self):
        rules = dict(self.config)
        boss = rules.get("boss")
        if boss == "bone":
            rules["mechanic"] = "guard"
            if self.phase >= 2:
                rules["pattern"] = "gold"
            if self.phase >= 3:
                rules["arena"] = "bones"
                rules.pop("mechanic", None)
        elif boss == "phantom":
            if self.phase >= 2:
                rules["mechanic"] = "phantom"
            if self.phase >= 3:
                rules["arena"] = "portals"
                rules["teleport"] = True
        elif boss == "saint":
            rules["objective"] = "core"
            rules["pattern"] = ("gold", "lanes", "alternating")[self.phase - 1]
            if self.phase >= 3:
                rules["arena"] = "moving"
        elif boss == "architect":
            if self.phase == 2:
                rules.update(balls=2, arena="portals")
            elif self.phase == 3:
                rules.update(pattern="alternating", objective="core")
            elif self.phase == 4:
                rules.update(arena="shrinking", pattern="gold")
            elif self.phase == 5:
                rules.update(objective="final", balls=1)
        return rules

    def expected_phase(self, hp):
        boss = self.config.get("boss")
        if boss == "architect":
            return 1 if hp > 7 else 2 if hp > 5 else 3 if hp > 3 else 4 if hp > 1 else 5
        return 1 if hp > 4 else 2 if hp > 2 else 3

    def configure_arena(self, game):
        arena = self.rules().get("arena")
        game.bounds = ARENA.copy()
        game.obstacles.clear()
        if arena == "bones":
            for y in (ARENA.top + 90, ARENA.bottom - 170):
                game.obstacles.append(Obstacle(pygame.Rect(620, y, 14, 80)))
        elif arena == "moving":
            game.obstacles.append(Obstacle(pygame.Rect(600, ARENA.centery - 65, 14, 130), hp=-1, moving=True))
        elif arena == "breakout":
            for i in range(4):
                game.obstacles.append(Obstacle(pygame.Rect(815, ARENA.top + 35 + i * 125, 22, 80), hp=2))

    def transition(self, game):
        if not self.config.get("boss") or game.enemy_hp <= 0:
            return
        phase = self.expected_phase(game.enemy_hp)
        if phase == self.phase:
            return
        self.phase = phase
        self.elapsed = 0
        self.warning = 0
        self.lanes.clear()
        self.pattern_clock = 3
        self.guard = 0
        self.guard_waiting_for_return = False
        self.player_shots = 0
        self.enemy_shots = 0
        self.arrow_charge = 0
        self.teleport_warning = 0
        game.projectiles.clear()
        self.configure_arena(game)
        game.serve()
        game.intro = 1.4
        game.invulnerability = 1.4
        notices = {
            "bone": {2: "BLOCK THE GOLD SHOTS", 3: "BREAK THE BONE WALLS"},
            "phantom": {2: "FOLLOW THE SOLID BALL", 3: "GATES OPEN. WATCH THE OUTLINE."},
            "saint": {2: "DODGE THE RED LANES", 3: "THE WALL STARTS MOVING"},
            "architect": {2: "TWO BALLS. OPEN GATES.", 3: "FIND THE OPEN CORE.",
                          4: "WALLS ARE CLOSING.", 5: "ONE BALL. ONE HIT."},
        }
        game.notice = notices[self.config["boss"]][phase]
        if phase == 5:
            game.player_hp = 1
            game.enemy_hp = 1
        game.impact(ARENA.centerx, ARENA.centery, VIOLET)

    def update(self, game, dt):
        self.elapsed += dt
        rules = self.rules()
        if self.guard > 0 and not self.guard_waiting_for_return:
            self.guard = max(0, self.guard - dt)
        for paddle in game.enemies:
            paddle.height = 145 if self.guard > 0 else (56 if len(game.enemies) > 1 else 88)
            paddle.move(0, game.bounds)
        if rules.get("arena") == "shrinking":
            inset = min(100, self.elapsed * 3)
            game.bounds = pygame.Rect(ARENA.left, ARENA.top + round(inset), ARENA.width, ARENA.height - round(inset) * 2)
            game.player.move(0, game.bounds)
        for obstacle in game.obstacles:
            obstacle.warning = max(0, obstacle.warning - dt)
            if obstacle.moving:
                obstacle.rect.centery = round(ARENA.centery + math.sin(self.elapsed * .7) * 155)
        self.core_open = self.elapsed % 5 < 3.6
        if self.arrow_charge > 0:
            self.arrow_charge -= dt
            if self.arrow_charge <= 0:
                origin = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
                game.projectiles.append(Projectile(origin, self.arrow_target, -game.direction * 470,
                                                      blockable=True, radius=7))
                game.impact(origin, self.arrow_target, GOLD)
        if rules.get("teleport"):
            self.teleport_cooldown -= dt
            if self.teleport_warning > 0:
                self.teleport_warning -= dt
                if self.teleport_warning <= 0 and game.enemies:
                    game.enemies[0].y = self.teleport_y
            elif self.teleport_cooldown <= 0 and game.enemies:
                self.teleport_y = game.rng.choice((ARENA.top + 110, ARENA.centery, ARENA.bottom - 110))
                self.teleport_warning = .7
                self.teleport_cooldown = 5
        if rules.get("objective") == "survive" and self.elapsed >= rules.get("duration", 35):
            game.clear_level()
            return
        pattern = rules.get("pattern")
        if not pattern:
            return
        if self.warning > 0:
            self.warning -= dt
            if self.warning <= 0:
                direction = -game.direction
                origin = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
                for y, blockable in self.lanes:
                    game.projectiles.append(Projectile(origin, y, direction * 310, blockable=blockable))
                self.lanes.clear()
                self.pattern_clock = 3.6
        else:
            self.pattern_clock -= dt
            if self.pattern_clock <= 0 and len(game.projectiles) < 5:
                self.pattern_count += 1
                # 190px safe channel exceeds paddle height + projectile diameter.
                # Aim once at the tell: never chase the player during the warning.
                if pattern in ("gold", "aimed"):
                    self.lanes = [(game.player.y, pattern == "gold")]
                else:
                    center = game.bounds.centery
                    gap = center + (100 if self.pattern_count % 2 else -100) if pattern == "alternating" else center
                    candidates = [game.bounds.top + 45 + i * (game.bounds.height - 90) / 4 for i in range(5)]
                    self.lanes = [(y, False) for y in candidates if abs(y - gap) >= 105]
                self.warning = .85

    def returned(self, game, ball, by_player):
        rules = self.rules()
        if by_player:
            self.player_shots += 1
            if rules.get("mechanic") == "guard" and self.player_shots % 3 == 0:
                # The guard is a response to this exact incoming ball. It remains
                # until the enemy actually returns it, so it cannot expire mid-flight.
                self.guard = 6.0
                self.guard_waiting_for_return = True
                game.callout("BONE GUARD", GOLD)
        else:
            self.enemy_shots += 1
            if self.guard_waiting_for_return:
                self.guard_waiting_for_return = False
                self.guard = .35
            if rules.get("mechanic") == "slime" and self.enemy_shots % 3 == 0:
                ball.slime = 2
                game.callout("SLIME COAT: 2 BOUNCES", (90, 255, 155))
            if rules.get("mechanic") == "phantom" and self.enemy_shots % 3 == 0:
                ball.phase_pending = True
                game.callout("PHASE AT MIDCOURT", VIOLET)
            if rules.get("mechanic") == "guard" and self.enemy_shots % 4 == 0 and self.arrow_charge <= 0:
                self.arrow_target = game.player.y
                self.arrow_charge = .75
                game.callout("ARROW: BLOCK OR REFLECT", GOLD)

    def wall_bounce(self, game, ball, at_top):
        rules = self.rules()
        if rules.get("arena") == "portals" and ball.portal_cooldown <= 0:
            ball.y = game.bounds.bottom - BALL_RADIUS - 1 if at_top else game.bounds.top + BALL_RADIUS + 1
            ball.portal_cooldown = .12
            ball.trail.clear()
            game.impact(ball.x, ball.y, VIOLET)
            return
        ball.y = game.bounds.top + BALL_RADIUS if at_top else game.bounds.bottom - BALL_RADIUS
        ball.vy = abs(ball.vy) if at_top else -abs(ball.vy)
        if ball.slime > 0:
            ball.slime -= 1
            ball.vy *= 1.3
        if ball.bank:
            ball.charged = True
            ball.vx *= 1.08
        ball.cap()
