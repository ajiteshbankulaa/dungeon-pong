"""Encounter rules, AI hooks, and bullet-hell monster ability systems for all 20 levels.

Monsters & Minibosses:
 1 SLIME         – Neon dripping slime coat on ball, organic acid pools at midcourt
 2 SKELETON      – Bone guard shield, 50% stun / 50% damage arrows, splinter shrapnel
 3 WRAITH        – Intelligent defensive Phase Step intercept, stealth phantom decoys
 4 NECROMANCER   – Dynamic bone spires erupting in ball's path on player hits, tracking soul embers
 5 BONE KING     – Boss 1: Guard -> Arrow volleys + splinters -> Dynamic bone spires
 6 THE MASON     – One-sided moving fortress wall (enemies shoot through, players bounce), Rubble Catapult
 7 THE HUNTER    – Rapid crimson sniper bolts (guaranteed damage unless 50% reflected), tracking laser
 8 THE TWINS     – Hyper-intelligent dual AI, synchronized multiball coverage
 9 GATEKEEPER    – Drifting Warp Rifts that bend ball paths, spatial pulses (no yellow arrows)
10 PHANTOM QUEEN – Boss 2: 5-shot fan spread, shadow illusions, portal rifts, phase steps
11 VAMPIRE KING  – Miniboss: Life-draining blood orbs, bat-swarm ball splits
12 DREAM EATER   – Miniboss: Nightmare gravity bending, hypnotic sleep waves
13 THE ALIEN     – Miniboss: Swarm UFOs, plasma death bursts, tractor beam pulses
14 THE VOID      – Miniboss: Gravitational singularity vortex pulling balls & shots to center
15 BULLET SAINT  – Boss 3: Geometric bullet hell protecting sacred core window
16 ZEUS          – Miniboss: Chain lightning bolts, electrified hyper-speed thunderballs
17 THE VAULT     – Breakout blocks, reactive kinetic shields, random kick returns
18 TWIN GATES    – Dual portal accelerators with +8% kinetic speed compounding
19 THE REFLECTION– Reverse side duel, top-wall dimensional tears
20 THE ARCHITECT – Final Boss: Master of all mechanics across 5 devastating phases
"""
import math
import pygame
from entities import Ball, Obstacle, Projectile, circle_rect
from settings import (ARENA, PLAYER_X, ENEMY_X, PADDLE_W, BALL_RADIUS,
                      BALL_START_SPEED, BALL_MAX_SPEED,
                      GOLD, VIOLET, RED, CYAN, WHITE,
                      HELL_RED, HOLY_GOLD, OCEAN_BLUE, NIRVANA_TEAL, clamp)

_ACID_LIFE = 3.5
_REANIMATE_CD = 5.0
_SOUL_EMBER_RALLY = 3


class Encounter:
    def __init__(self, config):
        self.config = config
        self.phase = 1
        self.elapsed = 0.0
        self.pattern_clock = 4.2
        self.warning = 0.0
        self.lanes = []
        self.fan = []
        self.pattern_count = 0
        # Guard (Skeleton / Bone King)
        self.guard = 0.0
        self.guard_waiting_for_return = False
        self.player_shots = 0
        self.enemy_shots = 0
        # Arrow / sniper charge
        self.arrow_charge = 0.0
        self.arrow_target = ARENA.centery
        # Teleport (Wraith / Phantom)
        self.teleport_warning = 0.0
        self.teleport_y = ARENA.centery
        self.teleport_cooldown = 4.5
        # Core (Bullet Saint)
        self.core_open = True
        # Necromancer spires
        self.spire_cd = 0.0
        self.reanimate_cd = 0.0
        self.spire_warning = 0.0
        self.spire_pending_y = None
        self._ember_clock = 2.8
        # Hunter retreat
        self.hunter_retreat = 0.0
        # Zeus lightning clock
        self._lightning_clock = 3.2
        # Void pulse clock
        self._void_clock = 3.5

    # ------------------------------------------------------------------ #
    #  Rules                                                               #
    # ------------------------------------------------------------------ #

    def rules(self):
        rules = dict(self.config)
        boss = rules.get("boss")
        if boss == "bone":
            rules["mechanic"] = "guard"
            if self.phase >= 2:
                rules["pattern"] = "gold"
            if self.phase >= 3:
                rules["arena"] = "bones"
                rules["mechanic"] = "necromancer"
        elif boss == "phantom":
            rules["pattern"] = "aimed"
            if self.phase >= 2:
                rules["mechanic"] = "phantom"
                rules["pattern"] = "fan"
            if self.phase >= 3:
                rules["arena"] = "portals"
                rules["teleport"] = True
                rules["pattern"] = "alternating"
        elif rules.get("mechanic") == "phantom":
            rules["teleport"] = True
        elif boss == "saint":
            rules["objective"] = "core"
            rules["pattern"] = ("gold", "lanes", "alternating")[self.phase - 1]
            if self.phase >= 3:
                rules["arena"] = "moving"
        elif boss == "lord666":
            rules["boss"] = "lord666"
            if self.phase == 1:
                rules.update(pattern="aimed", pattern_interval=3.4, projectile_speed=340)
            elif self.phase == 2:
                rules.update(pattern="fan", pattern_interval=3.0, projectile_speed=360)
            elif self.phase == 3:
                rules.update(pattern="alternating", pattern_interval=2.4, projectile_speed=400)
        elif boss == "architect":
            if self.phase == 2:
                rules.update(balls=2, arena="portals")
            elif self.phase == 3:
                rules.update(pattern="alternating", objective="core")
            elif self.phase == 4:
                rules.update(arena="shrinking", pattern="gold", mechanic="phantom")
            elif self.phase == 5:
                rules.update(objective="final", balls=1)
        return rules

    def expected_phase(self, hp):
        boss = self.config.get("boss")
        if boss == "architect":
            return 1 if hp > 9 else 2 if hp > 6 else 3 if hp > 3 else 4 if hp > 1 else 5
        if boss == "lord666":
            return 1 if hp > 5 else 2 if hp > 2 else 3
        return 1 if hp > 4 else 2 if hp > 2 else 3

    # ------------------------------------------------------------------ #
    #  Arena setup                                                         #
    # ------------------------------------------------------------------ #

    def configure_arena(self, game):
        arena = self.rules().get("arena")
        mechanic = self.rules().get("mechanic")
        game.bounds = ARENA.copy()
        game.obstacles.clear()
        self.spire_cd = 0.0
        self.reanimate_cd = 0.0
        self.spire_warning = 0.0
        self.spire_pending_y = None
        self._ember_clock = 2.8
        self.hunter_retreat = 0.0
        self._lightning_clock = 3.2
        self._void_clock = 3.5
        self.stasis_cooldown = 0.0
        self.holy_beam_clock = 3.2
        self.holy_beam_warning = 0.0
        self.holy_columns = []
        self.feather_clock = 3.8
        self.bubble_clock = 2.5
        self.mandala_split_cd = 0.0
        self.skull_volley_clock = 3.2
        self.magma_surge_clock = 4.0

        boss = self.rules().get("boss")
        if arena == "moving" or mechanic == "mason":
            # The Mason's one-sided fortress wall! Enemies shoot through, players bounce
            game.obstacles.append(
                Obstacle(pygame.Rect(600, ARENA.centery - 75, 20, 150),
                         hp=-1, moving=True, one_sided=True))
        elif arena == "bones":
            # Start with 1 dynamic bone spire (one-sided for enemy pass-through, 1 HP)
            game.obstacles.append(
                Obstacle(pygame.Rect(620, ARENA.top + 110, 16, 90),
                         hp=1, is_bone_spire=True, one_sided=True))

        elif arena == "breakout":
            for i in range(4):
                game.obstacles.append(
                    Obstacle(pygame.Rect(815, ARENA.top + 35 + i * 125, 22, 80), hp=2))
        elif mechanic == "gatekeeper":
            # Gatekeeper mid-court Warp Rifts (wormholes that redirect balls)
            game.obstacles.append(
                Obstacle(pygame.Rect(460, ARENA.centery - 130, 24, 60), hp=-1, is_warp_rift=True))
            game.obstacles.append(
                Obstacle(pygame.Rect(720, ARENA.centery + 70, 24, 60), hp=-1, is_warp_rift=True))
        elif mechanic == "alien":
            # The Alien tractor beam & orbiting drones
            game.obstacles.append(
                Obstacle(pygame.Rect(ARENA.centerx - 14, ARENA.centery - 90, 28, 180), hp=-1, is_tractor_beam=True))
            game.obstacles.append(
                Obstacle(pygame.Rect(ENEMY_X - 60, ARENA.centery - 65, 18, 18), hp=1, is_drone=True))
            game.obstacles.append(
                Obstacle(pygame.Rect(ENEMY_X - 60, ARENA.centery + 65, 18, 18), hp=1, is_drone=True))
        elif mechanic == "leviathan":
            # Leviathan swirling ocean whirlpool vortexes
            game.obstacles.append(
                Obstacle(pygame.Rect(450, ARENA.centery - 115, 52, 52), hp=-1, is_whirlpool=True))
            game.obstacles.append(
                Obstacle(pygame.Rect(670, ARENA.centery + 115, 52, 52), hp=-1, is_whirlpool=True))
        elif mechanic == "nirvana":
            # Nirvana sacred mandala stasis field
            game.obstacles.append(
                Obstacle(pygame.Rect(ARENA.centerx - 45, ARENA.centery - 45, 90, 90), hp=-1, is_mandala=True))

    # ------------------------------------------------------------------ #
    #  Phase transitions                                                   #
    # ------------------------------------------------------------------ #

    def transition(self, game):
        if not self.config.get("boss") or game.enemy_hp <= 0:
            return
        phase = self.expected_phase(game.enemy_hp)
        if phase == self.phase:
            return
        self.phase = phase
        self.elapsed = 0.0
        self.warning = 0.0
        self.lanes.clear()
        self.fan.clear()
        self.pattern_clock = 4.2
        self.guard = 0.0
        self.guard_waiting_for_return = False
        self.player_shots = 0
        self.enemy_shots = 0
        self.arrow_charge = 0.0
        self.teleport_warning = 0.0
        self.spire_cd = 0.0
        self.reanimate_cd = 0.0
        self.spire_warning = 0.0
        self.spire_pending_y = None
        game.projectiles.clear()
        game.balls = [b for b in game.balls if not b.decoy]
        self.configure_arena(game)
        game.serve()
        game.intro = 1.4
        game.invulnerability = 1.4
        notices = {
            "bone":      {2: "BLOCK THE GOLD SHOTS", 3: "DYNAMIC BONE SPIRES ERUPT"},
            "phantom":   {2: "FOLLOW THE SOLID BALL", 3: "GATES OPEN. WATCH THE OUTLINE."},
            "saint":     {2: "DODGE THE RED LANES", 3: "THE WALL STARTS MOVING"},
            "lord666":   {2: "HOMING SKULL VOLLEYS", 3: "HELLFIRE PENTAGRAM AWAKENS"},
            "architect": {2: "TWO BALLS. OPEN GATES.", 3: "FIND THE OPEN CORE.",
                          4: "WALLS CLOSING. PHANTOM COPIES.", 5: "ONE BALL. ONE HIT."},
        }
        game.notice = notices[self.config["boss"]][phase]
        if phase == 5:
            game.player_hp = 1
            game.enemy_hp = 1
        game.impact(ARENA.centerx, ARENA.centery, VIOLET)

    # ------------------------------------------------------------------ #
    #  Per-frame update                                                    #
    # ------------------------------------------------------------------ #

    def update(self, game, dt):
        self.elapsed += dt
        rules = self.rules()
        mechanic = rules.get("mechanic", "")
        lvl = self.config.get("level", 0)

        # ---- acid puddle timers -----------------------------------------
        for obs in list(game.obstacles):
            if obs.acid_timer > 0:
                obs.acid_timer -= dt
                if obs.acid_timer <= 0 and obs in game.obstacles:
                    game.obstacles.remove(obs)

        # ---- decoy ball lifetime ----------------------------------------
        for ball in list(game.balls):
            if ball.decoy and ball.decoy_life > 0:
                ball.decoy_life -= dt
                if ball.decoy_life <= 0 and ball in game.balls:
                    game.balls.remove(ball)

        # ---- guard sizing -----------------------------------------------
        if self.guard > 0 and not self.guard_waiting_for_return:
            self.guard = max(0.0, self.guard - dt)
        for paddle in game.enemies:
            paddle.height = 145 if self.guard > 0 else (56 if len(game.enemies) > 1 else 88)
            paddle.move(0, game.bounds)

        # ---- shrinking arena -------------------------------------------
        if rules.get("arena") == "shrinking":
            inset = min(100, self.elapsed * 3)
            game.bounds = pygame.Rect(
                ARENA.left, ARENA.top + round(inset),
                ARENA.width, ARENA.height - round(inset) * 2)
            game.player.move(0, game.bounds)

        # ---- obstacle warning countdown --------------------------------
        for obstacle in game.obstacles:
            if obstacle.warning > 0:
                obstacle.warning = max(0.0, obstacle.warning - dt)

        # ---- moving obstacle sinusoid ----------------------------------
        for obstacle in game.obstacles:
            if obstacle.moving:
                obstacle.rect.centery = round(ARENA.centery + math.sin(self.elapsed * .75) * 155)

        # ---- gatekeeper drifting warp rifts ----------------------------
        if mechanic == "gatekeeper":
            rifts = [o for o in game.obstacles if o.is_warp_rift]
            if len(rifts) == 2:
                rifts[0].rect.centery = round(ARENA.centery - 110 + math.sin(self.elapsed * 0.9) * 45)
                rifts[1].rect.centery = round(ARENA.centery + 100 - math.sin(self.elapsed * 0.9) * 45)

        # ---- core open/closed cycle ------------------------------------
        self.core_open = self.elapsed % 5 < 3.6

        # ---- arrow / sniper telegraph & fire ---------------------------
        if self.arrow_charge > 0:
            self.arrow_charge -= dt
            if self.arrow_charge <= 0:
                self._fire_arrow(game, rules)

        # ---- wraith / phantom intelligent teleport ---------------------
        if rules.get("teleport"):
            self.teleport_cooldown -= dt
            if self.teleport_warning > 0:
                self.teleport_warning -= dt
                if self.teleport_warning <= 0 and game.enemies:
                    game.enemies[0].y = self.teleport_y
            elif self.teleport_cooldown <= 0 and game.enemies:
                # Intelligent defensive intercept!
                incoming = [b for b in game.balls
                            if b.vx * game.direction > 0 and b.delay <= 0 and not b.decoy]
                enemy = game.enemies[0]
                if incoming:
                    ball = min(incoming, key=lambda b: abs(b.x - enemy.x))
                    predicted_y = game.predict_intercept(ball, enemy.x)
                    dist = abs(predicted_y - enemy.y)
                    travel_time = abs((enemy.x - ball.x) / max(1.0, abs(ball.vx)))
                    max_reach = game.config["speed"] * travel_time
                    # Phase step to intercept only if out of reach or emergency!
                    if dist > max_reach * 0.65:
                        self.teleport_y = clamp(predicted_y, game.bounds.top + 40, game.bounds.bottom - 40)
                        self.teleport_warning = 0.9
                        self.teleport_cooldown = 5.0
                        game.callout("PHASE INTERCEPT!", VIOLET, 0.9)
                        if game.audio:
                            game.audio.phantom_phase()
                    else:
                        self.teleport_cooldown = 2.0
                else:
                    self.teleport_y = game.rng.choice(
                        (ARENA.top + 110, ARENA.centery, ARENA.bottom - 110))
                    self.teleport_warning = 0.9
                    self.teleport_cooldown = 5.5
                    game.callout("PHASE STEP", VIOLET, 0.9)
                    if game.audio:
                        game.audio.phantom_phase()

        # ---- necromancer bone spire & ember sub-system -----------------
        if mechanic == "necromancer":
            self._update_necromancer(game, dt)

        # ---- zeus chain lightning (Level 16) ---------------------------
        if mechanic == "zeus":
            self._lightning_clock -= dt
            if self._lightning_clock <= 0 and game.state == "play":
                self._cast_zeus_lightning(game)
                self._lightning_clock = 3.6

        # ---- the void gravitational singularity (Level 14) ------------
        if mechanic == "void":
            self._update_void_singularity(game, dt)

        # ---- alien tractor beam & drones (Level 13) --------------------
        if mechanic == "alien":
            self._update_alien(game, dt)

        # ---- dream eater sleep stasis (Level 12) -----------------------
        if mechanic == "dreameater":
            self._update_dreameater(game, dt)

        # ---- the angel holy light columns (Level 21) -------------------
        if mechanic == "angel":
            self._update_angel(game, dt)

        # ---- leviathan oceanic drift & whirlpools (Level 22) -----------
        if mechanic == "leviathan":
            self._update_leviathan(game, dt)

        # ---- nirvana yin-yang mandala (Level 23) -----------------------
        if mechanic == "nirvana":
            self._update_nirvana(game, dt)

        # ---- lord 666 demonic arch-demon (Level 20) -------------------
        if rules.get("boss") == "lord666":
            self._update_lord666(game, dt)

        # ---- survival timer -------------------------------------------
        if rules.get("objective") == "survive" and self.elapsed >= rules.get("duration", 35):
            game.clear_level()
            return

        # ---- projectile patterns --------------------------------------
        self._update_patterns(game, dt, rules)

    # ------------------------------------------------------------------ #
    #  Arrow / sniper fire                                                #
    # ------------------------------------------------------------------ #

    def _fire_arrow(self, game, rules):
        origin = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
        name = self.config.get("name", "")

        if name == "THE HUNTER":
            # The Hunter: rapid high-velocity crimson sniper bolt!
            game.projectiles.append(
                Projectile(origin, self.arrow_target,
                           -game.direction * 920, vy=0,
                           blockable=False, hunter_bolt=True, radius=8))
            game.callout("SNIPER SHOT!", RED, 0.5)
            if game.audio:
                game.audio.laser_fire()
            self.hunter_retreat = 0.65

        elif name in ("SKELETON", "BONE KING"):
            # Skeleton / Bone King: standard arrows (50% stun / 50% damage)
            game.projectiles.append(
                Projectile(origin, self.arrow_target,
                           -game.direction * 640, vy=0,
                           blockable=True, arrow=True, radius=7))
            game.impact(origin, self.arrow_target, GOLD)
            if game.audio:
                game.audio.laser_fire()

    # ------------------------------------------------------------------ #
    #  Zeus & Void & Necromancer special mechanics                         #
    # ------------------------------------------------------------------ #

    def _cast_zeus_lightning(self, game):
        """Zeus strikes! Fast jagged electric bolt crackling toward player."""
        if not game.enemies:
            return
        origin = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
        target_y = clamp(game.player.y + game.rng.uniform(-40, 40),
                         ARENA.top + 30, ARENA.bottom - 30)
        p = Projectile(origin, target_y, -game.direction * 750,
                       blockable=False, lightning=True, radius=7)
        game.projectiles.append(p)
        game.callout("ZEUS THUNDER!", CYAN, 0.6)
        if game.audio:
            game.audio.shock_stun()

    def _update_void_singularity(self, game, dt):
        """The Void: singularity vortex at center exerts gravity on all balls."""
        cx, cy = ARENA.centerx, ARENA.centery
        for ball in game.balls:
            if ball.delay > 0:
                continue
            dx = cx - ball.x
            dy = cy - ball.y
            dist = max(40.0, math.hypot(dx, dy))
            force = 32000.0 / (dist * dist)
            ball.vx += (dx / dist) * force * dt
            ball.vy += (dy / dist) * force * dt
            ball.cap()

    def _update_necromancer(self, game, dt):
        """Reanimates destroyed bone spires and launches tracking soul embers."""
        # Spire reanimation
        if self.reanimate_cd > 0:
            self.reanimate_cd -= dt
            if self.reanimate_cd <= 0 and game.state == "play":
                spire_count = len([o for o in game.obstacles if o.is_bone_spire])
                if spire_count < 3:
                    self._spawn_dynamic_spire(game, ARENA.centery + game.rng.choice((-90, 0, 90)))
                    self.reanimate_cd = _REANIMATE_CD

        # Spire warning countdown
        for obs in list(game.obstacles):
            if obs.warning > 0:
                obs.warning -= dt
                if obs.warning <= 0:
                    obs.warning = 0.0
                    if game.audio:
                        game.audio.bone_spawn()

        # Soul embers in active rallies
        if game.rally >= _SOUL_EMBER_RALLY:
            self._ember_clock -= dt
            if self._ember_clock <= 0:
                self._emit_soul_ember(game)
                self._ember_clock = max(1.8, 3.4 - game.rally * 0.12)

    def _spawn_dynamic_spire(self, game, y):
        """Places a dynamic bone spire in the court (one-sided, 1 HP)."""
        spire_x = 620
        obs = Obstacle(
            pygame.Rect(spire_x, round(y) - 50, 16, 100),
            hp=1, warning=0.45, is_bone_spire=True, one_sided=True)
        game.obstacles.append(obs)
        game.callout("BONE SPIRE!", VIOLET, 0.5)


    def _emit_soul_ember(self, game):
        """Launches a slow homing soul ember from enemy toward player."""
        if not game.enemies:
            return
        origin_x = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
        ey = game.enemies[0].y
        dx = game.player.x - origin_x
        dy = game.player.y - ey
        dist = max(1.0, math.hypot(dx, dy))
        speed = 190
        p = Projectile(
            origin_x, ey,
            vx=-game.direction * speed * abs(dx) / dist,
            vy=speed * dy / dist,
            blockable=False, radius=6, soul_ember=True)
        game.projectiles.append(p)
        game.callout("SOUL EMBER", VIOLET, 0.6)
        if game.audio:
            game.audio.soul_ember()

    # ------------------------------------------------------------------ #
    #  Callbacks from game.py                                              #
    # ------------------------------------------------------------------ #

    def returned(self, game, ball, by_player):
        rules = self.rules()
        mechanic = rules.get("mechanic", "")
        name = self.config.get("name", "")
        lvl = self.config.get("level", 0)

        if by_player:
            self.player_shots += 1
            # Skeleton / Bone King: guard on every 3rd player shot
            if mechanic == "guard" and self.player_shots % 3 == 0:
                self.guard = 6.0
                self.guard_waiting_for_return = True
                game.callout("BONE GUARD", GOLD)

            # Necromancer: dynamic bone spire directly in ball's flight path!
            if mechanic == "necromancer":
                spire_count = len([o for o in game.obstacles if o.is_bone_spire])
                if spire_count < 3 and game.rng.random() < 0.65:
                    predicted_y = clamp(ball.y + ball.vy * 0.28, ARENA.top + 70, ARENA.bottom - 70)
                    self._spawn_dynamic_spire(game, predicted_y)

        else:
            self.enemy_shots += 1
            if self.guard_waiting_for_return:
                self.guard_waiting_for_return = False
                self.guard = 0.35

            # Slime: coat ball in green slime + drop organic acid pool
            if mechanic == "slime" and self.enemy_shots % 3 == 0:
                ball.slime = 2
                game.callout("SLIME COAT!", (90, 255, 120))
                self._drop_acid_puddle(game, ball)

            # Wraith / Phantom Queen: stealth phantom decoys
            if mechanic == "phantom" and self.enemy_shots % 2 == 0:
                ball.phase_pending = True
                ball._spawn_decoys_pending = True
                game.callout("PHANTOM SPLIT", VIOLET)

            # Skeleton / Bone King: arrows
            if mechanic == "guard" and self.enemy_shots % 4 == 0 and self.arrow_charge <= 0:
                self.arrow_target = game.player.y
                self.arrow_charge = 0.75
                game.callout("ARROW INCOMING", GOLD)


            # The Hunter: locks sniper laser sight
            if name == "THE HUNTER" and self.arrow_charge <= 0:
                self.arrow_target = game.player.y
                self.arrow_charge = 1.2
                game.callout("SNIPER LOCKED", RED, 1.2)

            # The Mason: Rubble Catapult! Launches flying stone boulders
            if mechanic == "mason" and self.enemy_shots % 3 == 0:
                self._launch_mason_rubble(game)

            # Vampire King: Bat swarm split
            if mechanic == "vampire" and self.enemy_shots % 4 == 0 and len(game.balls) < 3:
                self._split_ball(game, ball)
                game.callout("BAT SWARM!", RED)

            # Zeus: hyper-charge thunderball
            if mechanic == "zeus" and self.enemy_shots % 3 == 0:
                ball.vx *= 1.25
                ball.charged = True
                ball.cap()
                game.callout("THUNDER CHARGE!", CYAN)

    def _launch_mason_rubble(self, game):
        """The Mason catapults flying stone rubble across the arena."""
        origin = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
        for vy in (-120, 120):
            game.projectiles.append(
                Projectile(origin, ARENA.centery + vy * 0.5,
                           -game.direction * 420, vy=vy,
                           blockable=False, stone_rubble=True, radius=9))
        game.callout("RUBBLE SLAM!", WHITE, 0.5)
        if game.audio:
            game.audio.bone_break()

    def _drop_acid_puddle(self, game, ball):
        """Drop an organic acid puddle at midcourt."""
        px = round(clamp(ball.x, ARENA.left + 80, ARENA.right - 80))
        py = round(clamp(ball.y, ARENA.top + 40, ARENA.bottom - 40))
        puddles = [o for o in game.obstacles if o.acid_timer > 0]
        if len(puddles) >= 2:
            return
        obs = Obstacle(
            pygame.Rect(px - 30, py - 14, 60, 28),
            hp=-1, warning=0.0, acid_timer=_ACID_LIFE)
        game.obstacles.append(obs)
        if game.audio:
            game.audio.acid_splat()

    def _split_ball(self, game, ball):
        """Forks the ball into a sibling with mirrored vy."""
        sibling = Ball(
            x=ball.x, y=ball.y,
            vx=ball.vx, vy=-ball.vy,
            delay=0, returned=ball.returned)
        game.balls.append(sibling)

    def maybe_spawn_decoys(self, game, ball):
        """Called by game.py when phase_pending ball crosses midcourt."""
        if not getattr(ball, "_spawn_decoys_pending", False):
            return
        ball._spawn_decoys_pending = False
        self._spawn_wraith_decoys(game, ball)

    def _spawn_wraith_decoys(self, game, ball):
        """Spawn 2 stealth phantom decoys on randomized lanes."""
        base_speed = math.hypot(ball.vx, ball.vy)
        for offset_y, angle_diff in ((-70, -0.36), (70, 0.36)):
            spawn_y = clamp(ball.y + offset_y, ARENA.top + 40, ARENA.bottom - 40)
            angle = math.atan2(ball.vy, ball.vx) + angle_diff
            decoy = Ball(
                x=ball.x,
                y=spawn_y,
                vx=base_speed * math.cos(angle),
                vy=base_speed * math.sin(angle),
                delay=0,
                decoy=True,
                decoy_life=3.0,
            )
            decoy.cap()
            game.balls.append(decoy)
        if game.audio:
            game.audio.phantom_phase()

    def arrow_reflected(self, game):
        """Bone King / Skeleton: bone splinter fires when arrow is blocked/reflected."""
        mechanic = self.rules().get("mechanic", "")
        if "guard" in mechanic or mechanic == "necromancer":
            origin = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
            splinter = Projectile(origin, self.arrow_target,
                                  -game.direction * 650, blockable=False, radius=5)
            game.projectiles.append(splinter)
            game.callout("BONE SPLINTER!", GOLD, 0.55)

    def swarm_paddle_destroyed(self, game, paddle):
        """Alien / Swarm: each destroyed paddle fires a 3-shot retaliatory plasma burst."""
        origin_x = paddle.x
        origin_y = paddle.y
        for vy_off in (-110, 0, 110):
            p = Projectile(origin_x, origin_y,
                           -game.direction * 360, vy=vy_off,
                           blockable=False, radius=6)
            game.projectiles.append(p)
        game.callout("PLASMA BURST!", CYAN, 0.6)
        if game.audio:
            game.audio.laser_fire()

    def wall_bounce(self, game, ball, at_top):
        rules = self.rules()
        lvl = self.config.get("level", 0)

        # Portal wrap
        if rules.get("arena") == "portals" and ball.portal_cooldown <= 0:
            ball.y = (game.bounds.bottom - BALL_RADIUS - 1
                      if at_top else game.bounds.top + BALL_RADIUS + 1)
            ball.portal_cooldown = 0.12
            ball.trail.clear()
            game.impact(ball.x, ball.y, VIOLET)
            # Level 18: compounding speed boost
            if lvl == 18:
                speed = math.hypot(ball.vx, ball.vy)
                new_speed = min(BALL_MAX_SPEED, speed * 1.08)
                ball.vx *= new_speed / max(1, speed)
                ball.vy *= new_speed / max(1, speed)
            return

        # Normal bounce
        ball.y = (game.bounds.top + BALL_RADIUS if at_top
                  else game.bounds.bottom - BALL_RADIUS)
        ball.vy = abs(ball.vy) if at_top else -abs(ball.vy)

        # Level 19: top-wall dimensional tear
        if lvl == 19 and at_top:
            ball.y = game.rng.uniform(game.bounds.top + BALL_RADIUS + 20,
                                      game.bounds.bottom - BALL_RADIUS - 20)
            ball.vy = game.rng.choice([-1, 1]) * abs(ball.vy)
            game.impact(ball.x, ball.y, VIOLET)

        # Slime boost
        if ball.slime > 0:
            ball.slime -= 1
            ball.vy *= 1.34

        # Ricochet & Inferno
        if ball.bank:
            ball.charged = True
            ball.vx *= 1.08

        if "INFERNO" in game.powers:
            game.inferno_banks += 1
            if game.inferno_banks >= 2:
                ball.fireball = True
                ball.fireball_timer = 4.0
                game.callout("INFERNO IGNITED!", (255, 100, 20), 0.7)
                if game.audio:
                    game.audio.laser_fire()

        ball.cap()

    def obstacle_destroyed(self, game, obstacle):
        if game.audio:
            game.audio.bone_break()
        mechanic = self.rules().get("mechanic", "")
        if mechanic in ("necromancer", "guard"):
            self.reanimate_cd = _REANIMATE_CD

    # ------------------------------------------------------------------ #
    #  Projectile patterns                                                 #
    # ------------------------------------------------------------------ #

    def _update_patterns(self, game, dt, rules):
        pattern = rules.get("pattern")
        if not pattern:
            return
        if self.warning > 0:
            self.warning -= dt
            if self.warning <= 0:
                direction = -game.direction
                origin = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
                for y, blockable in self.lanes:
                    speed = rules.get("projectile_speed", 290)
                    game.projectiles.append(
                        Projectile(origin, y, direction * speed, blockable=blockable))
                    if game.audio:
                        game.audio.laser_fire()
                for y, vy in self.fan:
                    game.projectiles.append(
                        Projectile(origin, y, direction * 310, vy=vy))
                    if game.audio:
                        game.audio.laser_fire()
                self.lanes.clear()
                self.fan.clear()
                self.pattern_clock = rules.get("pattern_interval", 4.5)
        else:
            self.pattern_clock -= dt
            if self.pattern_clock <= 0 and len(game.projectiles) < 6:
                self.pattern_count += 1
                self._build_pattern(game, rules, pattern)
                self.warning = rules.get("warning", 1.0)

    def _build_pattern(self, game, rules, pattern):
        center = game.bounds.centery
        if pattern == "fan":
            origin_y = game.enemies[0].y if game.enemies else center
            target = game.player.y
            travel = max(.5, abs((game.player.x - ENEMY_X) / 310))
            targets = [max(game.bounds.top + 30, min(game.bounds.bottom - 30, target + offset))
                       for offset in (-160, -60, 0, 60, 160)]
            self.fan = [(origin_y, (ty - origin_y) / travel) for ty in targets]
            game.callout("SPREAD FIRE – FIND THE GAP", VIOLET, rules.get("warning", 1.0))
        elif pattern in ("gold", "aimed"):
            self.lanes = [(game.player.y, pattern == "gold")]
        elif pattern == "blood":
            # Vampire King: 2 blood orbs aimed high and low
            self.lanes = [(game.player.y - 70, False), (game.player.y + 70, False)]
        else:
            gap = center + (110 if self.pattern_count % 2 else -110) \
                if pattern == "alternating" else center
            candidates = [game.bounds.top + 45 + i * (game.bounds.height - 90) / 4
                          for i in range(5)]
            self.lanes = [(y, False) for y in candidates if abs(y - gap) >= 105]

    # ------------------------------------------------------------------ #
    #  Curated Monster & Mythic Mechanics                                 #
    # ------------------------------------------------------------------ #

    def _update_alien(self, game, dt):
        """The Alien: orbit defense drones and tractor beam ball captures."""
        drones = [o for o in game.obstacles if o.is_drone]
        for i, drone in enumerate(drones):
            ang = self.elapsed * 2.2 + i * math.pi
            drone.rect.centerx = round(ENEMY_X - 65 + math.cos(ang) * 45)
            drone.rect.centery = round(ARENA.centery + math.sin(ang) * 90)

        tractors = [o for o in game.obstacles if o.is_tractor_beam]
        if tractors:
            tr = tractors[0]
            for ball in game.balls:
                if ball.portal_cooldown <= 0 and ball.stasis_timer <= 0:
                    if tr.rect.collidepoint(ball.x, ball.y):
                        ball.stasis_timer = 0.4
                        ball.stasis_vx = -abs(ball.vx) * 1.15
                        ball.stasis_vy = game.rng.choice((-180, -90, 90, 180))
                        ball.portal_cooldown = 1.0
                        game.callout("TRACTOR LAUNCH!", CYAN, 0.5)
                        game.impact(ball.x, ball.y, CYAN)

    def _update_dreameater(self, game, dt):
        """Dream Eater: Sleep Stasis Trap that freezes balls mid-court."""
        if self.stasis_cooldown > 0:
            self.stasis_cooldown -= dt
        for ball in game.balls:
            if self.stasis_cooldown <= 0 and abs(ball.x - ARENA.centerx) < 30 and ball.stasis_timer <= 0:
                ball.stasis_timer = 0.55
                ball.stasis_vx = ball.vx * 1.2
                ball.stasis_vy = -ball.vy * 1.3 if abs(ball.vy) > 40 else game.rng.choice((-150, 150))
                self.stasis_cooldown = 4.2
                game.callout("SLEEP STASIS TRAP!", VIOLET, 0.7)
                game.impact(ball.x, ball.y, VIOLET)

    def _update_angel(self, game, dt):
        """The Angel: Holy light column warnings + spinning holy daggers."""
        self.holy_beam_clock -= dt
        if self.holy_beam_warning > 0:
            self.holy_beam_warning -= dt
            if 0 < self.holy_beam_warning <= 0.35:
                # Active light pillar strike!
                for col_x in self.holy_columns:
                    if abs(game.player.x - col_x) < 28 and game.invulnerability <= 0:
                        game.player.stun = 0.6
                        game.callout("SMITTEN!", HOLY_GOLD, 0.5)
                        game.hurt()
            elif self.holy_beam_warning <= 0:
                self.holy_columns = []
        elif self.holy_beam_clock <= 0:
            self.holy_columns = [ARENA.left + 220, ARENA.left + 460]
            self.holy_beam_warning = 1.1
            self.holy_beam_clock = 4.5
            game.callout("DIVINE RETRIBUTION!", HOLY_GOLD, 1.0)

        self.feather_clock -= dt
        if self.feather_clock <= 0 and len(game.projectiles) < 6:
            origin_y = game.enemies[0].y if game.enemies else ARENA.centery
            for vy in (-110, 0, 110):
                p = Projectile(ENEMY_X, origin_y, -320, vy=vy, holy_feather=True, blockable=True, radius=5)
                game.projectiles.append(p)
            self.feather_clock = 3.6

    def _update_leviathan(self, game, dt):
        """Leviathan: Oceanic drift currents and whirlpool vortexes."""
        for ball in game.balls:
            ball.vy += math.sin(self.elapsed * 2.4 + ball.x * 0.015) * 160 * dt

        wps = [o for o in game.obstacles if o.is_whirlpool]
        for wp in wps:
            for ball in game.balls:
                dx = wp.rect.centerx - ball.x
                dy = wp.rect.centery - ball.y
                dist = math.hypot(dx, dy)
                if 8 < dist < 95:
                    pull = (95 - dist) * 1.9 * dt
                    ball.vx += (dx / dist) * pull
                    ball.vy += (dy / dist) * pull + (dx / dist) * pull * 0.4

        self.bubble_clock -= dt
        if self.bubble_clock <= 0 and len(game.projectiles) < 4:
            p = Projectile(ENEMY_X, game.rng.uniform(ARENA.top + 40, ARENA.bottom - 40),
                           -210, vy=math.sin(self.elapsed * 2.0) * 45,
                           bubble=True, blockable=True, radius=9)
            game.projectiles.append(p)
            self.bubble_clock = 2.8

    def _update_nirvana(self, game, dt):
        """Nirvana: Sacred mandala splitting balls into Yin-Yang duality."""
        if self.mandala_split_cd > 0:
            self.mandala_split_cd -= dt
        mandalas = [o for o in game.obstacles if o.is_mandala]
        if mandalas and self.mandala_split_cd <= 0 and len(game.balls) < 2:
            m = mandalas[0]
            for ball in list(game.balls):
                if circle_rect(ball.x, ball.y, BALL_RADIUS, m.rect):
                    ball.yin_yang = 1
                    ball.vy = -abs(ball.vy) - 40
                    yang = Ball(x=ball.x, y=ball.y, vx=ball.vx * 0.95, vy=abs(ball.vy) + 40,
                                delay=0, returned=ball.returned, yin_yang=-1)
                    game.balls.append(yang)
                    self.mandala_split_cd = 8.0
                    game.callout("YIN-YANG DUALITY!", NIRVANA_TEAL, 0.9)
                    game.impact(ball.x, ball.y, NIRVANA_TEAL)

    def _update_lord666(self, game, dt):
        """Lord 666: Demonic flaming skulls and magma surges."""
        self.skull_volley_clock -= dt
        if self.skull_volley_clock <= 0 and len(game.projectiles) < 6:
            origin_y = game.enemies[0].y if game.enemies else ARENA.centery
            for vy_off in (-90, 90):
                p = Projectile(ENEMY_X, origin_y + vy_off * 0.5, -340, vy=vy_off,
                               hellfire_skull=True, blockable=True, radius=8)
                game.projectiles.append(p)
            self.skull_volley_clock = 3.6 if self.phase == 1 else 2.6
            game.callout("HELLFIRE SKULLS!", HELL_RED, 0.7)
