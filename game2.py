"""
Roulette Pong — "It's Pong, but every time someone scores a point, a wild rule mutation takes over!"
Assignment: "This, but That" Game Evolution Prototype.

Play modes:
  - 1 Player (vs Adaptive AI)
  - 2 Players (Local Couch: P1 = W/S, P2 = Up/Down)

Run:
  python game2.py
  python game2.py --smoke
"""

import argparse
import array
import math
import os
import random
import sys
import pygame

# --- Window & Physics Constants ---
WIDTH, HEIGHT = 1000, 640
ARENA = pygame.Rect(40, 70, 920, 520)
PADDLE_W = 14
DEFAULT_PADDLE_H = 96
PADDLE_SPEED = 520.0
P1_X = ARENA.left + 30
P2_X = ARENA.right - 30 - PADDLE_W
BALL_RADIUS = 9
BASE_BALL_SPEED = 420.0
MAX_BALL_SPEED = 780.0
SCORE_LIMIT = 7

# --- Color Palette ---
COLOR_BG = (12, 14, 22)
COLOR_ARENA_BORDER = (45, 52, 75)
COLOR_TEXT = (240, 242, 250)
COLOR_MUTED = (130, 138, 160)
COLOR_P1 = (45, 230, 255)      # Electric Cyan
COLOR_P2 = (255, 60, 110)      # Neon Crimson
COLOR_BALL = (255, 255, 255)
COLOR_MUTATOR = (255, 220, 60) # Golden Yellow


# --- Pure Mathematical Synthesized Sound Engine (Zero external assets) ---
class SoundEngine:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.sounds = {}
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._generate_sfx()
        except Exception:
            self.enabled = False

    def _synth_wave(self, duration_s, freq_func):
        sample_rate = 22050
        n_samples = int(sample_rate * duration_s)
        buf = array.array("h")
        phase = 0.0
        for i in range(n_samples):
            t = i / sample_rate
            f = freq_func(t, duration_s)
            phase += 2.0 * math.pi * f / sample_rate
            amp = max(0.0, 1.0 - (t / duration_s) ** 1.5)
            sample_val = int(amp * math.sin(phase) * 16000)
            buf.append(max(-32767, min(32767, sample_val)))
        return pygame.mixer.Sound(buffer=buf)

    def _generate_sfx(self):
        try:
            # Crisp high paddle tap
            self.sounds["paddle"] = self._synth_wave(0.06, lambda t, d: 480 + 320 * (1 - t / d))
            # Lower hollow wall bounce
            self.sounds["wall"] = self._synth_wave(0.05, lambda t, d: 240)
            # Goal score explosion / drop
            self.sounds["score"] = self._synth_wave(0.35, lambda t, d: 260 - 180 * (t / d))
            # Dramatic mutator roulette spin / alert
            self.sounds["mutator"] = self._synth_wave(0.28, lambda t, d: 440 + 440 * math.sin(t * 30))
            # Victory triumphant fanfare
            self.sounds["win"] = self._synth_wave(0.60, lambda t, d: 380 + 300 * (t / d))
        except Exception:
            self.enabled = False

    def play(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass


# --- Mutator Definitions ---
# Each point scored rolls one of these active gameplay mutators!
MUTATORS = [
    {
        "id": "NORMAL",
        "name": "PURE PONG",
        "desc": "Standard tournament physics. High focus, no gimmicks!",
        "banner_col": (200, 205, 220),
    },
    {
        "id": "MULTIBALL",
        "name": "TRI-BALL FRENZY",
        "desc": "3 balls served at once! First ball to pass either paddle scores.",
        "banner_col": (255, 110, 40),
    },
    {
        "id": "SUPERNOVA",
        "name": "SUPERNOVA SPEED",
        "desc": "Ball velocity boosted by 175%! Lightning reflexes required.",
        "banner_col": (255, 45, 80),
    },
    {
        "id": "GRAVITY",
        "name": "SINGULARITY WELL",
        "desc": "A cosmic gravity core in the center bends all ball trajectories!",
        "banner_col": (190, 80, 255),
    },
    {
        "id": "TINY",
        "name": "MICRO PADDLES",
        "desc": "Both paddles shrink to 45% size! Needle-thread precision.",
        "banner_col": (255, 70, 70),
    },
    {
        "id": "TITAN",
        "name": "TITAN SHIELDS",
        "desc": "Paddles expand to 160% size! Long rallies, rapid returns.",
        "banner_col": (40, 240, 160),
    },
    {
        "id": "CURVEBALL",
        "name": "MAGNUS CURVE",
        "desc": "Paddle motion imparts wild aerodynamic spin & trajectory curves!",
        "banner_col": (45, 180, 255),
    },
    {
        "id": "GHOST",
        "name": "GHOST BALL",
        "desc": "The ball turns completely invisible while crossing mid-court!",
        "banner_col": (140, 150, 220),
    },
    {
        "id": "INVERTED",
        "name": "NEURAL INVERSION",
        "desc": "Both players' controls are upside-down (Up is Down, Down is Up)!",
        "banner_col": (255, 190, 30),
    },
    {
        "id": "PORTALS",
        "name": "WARP RIFTS",
        "desc": "Twin portals in midcourt teleport the ball across dimensions!",
        "banner_col": (30, 255, 235),
    },
]


class Ball:
    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.spin = 0.0
        self.trail = []
        self.portal_cd = 0.0

    @property
    def rect(self):
        return pygame.Rect(round(self.x - BALL_RADIUS), round(self.y - BALL_RADIUS),
                           BALL_RADIUS * 2, BALL_RADIUS * 2)

    def cap_speed(self, max_s=MAX_BALL_SPEED):
        s = math.hypot(self.vx, self.vy)
        if s > max_s:
            scale = max_s / s
            self.vx *= scale
            self.vy *= scale
        if abs(self.vx) < 180.0:
            self.vx = 180.0 if self.vx >= 0 else -180.0


class Paddle:
    def __init__(self, x, y, h=DEFAULT_PADDLE_H):
        self.x = float(x)
        self.y = float(y)
        self.h = float(h)
        self.vy = 0.0

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), PADDLE_W, round(self.h))

    def move(self, dy, bounds):
        self.y = max(bounds.top + 4, min(bounds.bottom - self.h - 4, self.y + dy))


class RoulettePong:
    def __init__(self, mode="1P", sound=True):
        self.mode = mode   # "1P" or "2P"
        self.sound = SoundEngine(sound)
        self.state = "MENU"  # "MENU", "PLAY", "GAMEOVER"
        self.p1_score = 0
        self.p2_score = 0
        self.winner = None

        self.p1 = Paddle(P1_X, ARENA.centery - DEFAULT_PADDLE_H / 2)
        self.p2 = Paddle(P2_X, ARENA.centery - DEFAULT_PADDLE_H / 2)
        self.balls = []

        self.current_mutator = MUTATORS[0]
        self.mutator_timer = 0.0
        self.serve_delay = 0.0

        # AI internals
        self.ai_target_y = ARENA.centery
        self.ai_timer = 0.0
        self.ai_error = 0.0

        # Portals geometry
        self.portal1 = pygame.Rect(ARENA.centerx - 12, ARENA.top + 90, 24, 70)
        self.portal2 = pygame.Rect(ARENA.centerx - 12, ARENA.bottom - 160, 24, 70)

        # Visual shake & flashes
        self.screen_shake = 0.0
        self.banner_scale = 1.0

        self.reset_match()

    def reset_match(self):
        self.p1_score = 0
        self.p2_score = 0
        self.winner = None
        self.current_mutator = MUTATORS[0]
        self.apply_mutator(self.current_mutator, is_first=True)

    def apply_mutator(self, mut, is_first=False):
        self.current_mutator = mut
        self.mutator_timer = 1.8
        self.banner_scale = 1.4

        # Resize paddles based on mutator
        h = DEFAULT_PADDLE_H
        if mut["id"] == "TINY":
            h = DEFAULT_PADDLE_H * 0.45
        elif mut["id"] == "TITAN":
            h = DEFAULT_PADDLE_H * 1.60

        self.p1.h = h
        self.p2.h = h
        self.p1.move(0, ARENA)
        self.p2.move(0, ARENA)

        if not is_first:
            self.sound.play("mutator")
        self.spawn_serve()

    def spawn_serve(self, to_player=None):
        self.balls.clear()
        self.serve_delay = 0.9

        dir_x = 1 if (to_player == 2 or (to_player is None and random.random() < 0.5)) else -1
        speed = BASE_BALL_SPEED * (1.75 if self.current_mutator["id"] == "SUPERNOVA" else 1.0)

        if self.current_mutator["id"] == "MULTIBALL":
            for angle in (-0.35, 0.0, 0.35):
                vx = dir_x * speed * math.cos(angle)
                vy = speed * math.sin(angle)
                self.balls.append(Ball(ARENA.centerx, ARENA.centery, vx, vy))
        else:
            angle = random.uniform(-0.30, 0.30)
            vx = dir_x * speed * math.cos(angle)
            vy = speed * math.sin(angle)
            self.balls.append(Ball(ARENA.centerx, ARENA.centery, vx, vy))

    def spin_next_mutator(self):
        # Pick a fun mutator different from the current one
        candidates = [m for m in MUTATORS if m["id"] != self.current_mutator["id"]]
        next_mut = random.choice(candidates)
        self.apply_mutator(next_mut)

    def update(self, dt, p1_input, p2_input):
        if self.state != "PLAY":
            return

        self.screen_shake = max(0.0, self.screen_shake - dt * 10)
        self.mutator_timer = max(0.0, self.mutator_timer - dt)

        # Inverted controls mutator
        inv = -1 if self.current_mutator["id"] == "INVERTED" else 1
        self.p1.move(p1_input * inv * PADDLE_SPEED * dt, ARENA)

        if self.mode == "2P":
            self.p2.move(p2_input * inv * PADDLE_SPEED * dt, ARENA)
        else:
            self._update_ai(dt)

        if self.serve_delay > 0:
            self.serve_delay -= dt
            return

        # Update each ball
        scored = False
        scorer = None

        for ball in list(self.balls):
            ball.portal_cd = max(0.0, ball.portal_cd - dt)
            ball.trail.append((ball.x, ball.y))
            ball.trail = ball.trail[-6:]

            # Mutator: Singularity Gravity Well
            if self.current_mutator["id"] == "GRAVITY":
                dx = ARENA.centerx - ball.x
                dy = ARENA.centery - ball.y
                dist = max(30.0, math.hypot(dx, dy))
                force = 45000.0 / (dist * dist)
                ball.vx += (dx / dist) * force * dt
                ball.vy += (dy / dist) * force * dt

            # Mutator: Curveball Spin
            if self.current_mutator["id"] == "CURVEBALL" and abs(ball.spin) > 0.1:
                ball.vy += ball.spin * 380.0 * dt
                ball.spin *= (1.0 - dt * 1.5)

            ball.cap_speed()
            ball.x += ball.vx * dt
            ball.y += ball.vy * dt

            # Wall Collisions (Top / Bottom)
            bounce_boost = 1.25 if self.current_mutator["id"] == "BOUNCY" else 1.0
            if ball.y <= ARENA.top + BALL_RADIUS:
                ball.y = ARENA.top + BALL_RADIUS
                ball.vy = abs(ball.vy) * bounce_boost
                self.sound.play("wall")
            elif ball.y >= ARENA.bottom - BALL_RADIUS:
                ball.y = ARENA.bottom - BALL_RADIUS
                ball.vy = -abs(ball.vy) * bounce_boost
                self.sound.play("wall")

            # Mutator: Portals
            if self.current_mutator["id"] == "PORTALS" and ball.portal_cd <= 0:
                if self.portal1.collidepoint(ball.x, ball.y):
                    ball.x = self.portal2.centerx
                    ball.y = self.portal2.centery
                    ball.portal_cd = 0.5
                    self.sound.play("wall")
                elif self.portal2.collidepoint(ball.x, ball.y):
                    ball.x = self.portal1.centerx
                    ball.y = self.portal1.centery
                    ball.portal_cd = 0.5
                    self.sound.play("wall")

            # Paddle Collisions
            # Player 1 (Left)
            if ball.vx < 0 and self.p1.rect.colliderect(ball.rect):
                ball.x = self.p1.rect.right + BALL_RADIUS
                self._handle_paddle_hit(ball, self.p1, p1_input, 1)

            # Player 2 / AI (Right)
            if ball.vx > 0 and self.p2.rect.colliderect(ball.rect):
                ball.x = self.p2.rect.left - BALL_RADIUS
                self._handle_paddle_hit(ball, self.p2, p2_input if self.mode == "2P" else 0, -1)

            # Scoring check
            if ball.x < ARENA.left:
                scored = True
                scorer = 2
                break
            elif ball.x > ARENA.right:
                scored = True
                scorer = 1
                break

        if scored:
            self._handle_point(scorer)

    def _handle_paddle_hit(self, ball, paddle, move_input, direction):
        rel_y = (ball.y - (paddle.y + paddle.h / 2)) / (paddle.h / 2)
        rel_y = max(-1.0, min(1.0, rel_y))
        speed = math.hypot(ball.vx, ball.vy) * 1.05
        angle = rel_y * (math.pi / 3.2)  # up to ~56 degree deflection

        ball.vx = direction * speed * math.cos(angle)
        ball.vy = speed * math.sin(angle)

        if self.current_mutator["id"] == "CURVEBALL":
            ball.spin = move_input

        ball.cap_speed()
        self.sound.play("paddle")
        self.screen_shake = 3.5

    def _handle_point(self, scorer):
        if scorer == 1:
            self.p1_score += 1
        else:
            self.p2_score += 1

        self.sound.play("score")
        self.screen_shake = 7.0

        if self.p1_score >= SCORE_LIMIT:
            self.state = "GAMEOVER"
            self.winner = "PLAYER 1"
            self.sound.play("win")
        elif self.p2_score >= SCORE_LIMIT:
            self.state = "GAMEOVER"
            self.winner = "PLAYER 2" if self.mode == "2P" else "THE AI"
            self.sound.play("win")
        else:
            # Cycle to the next wild random rule mutation!
            self.spin_next_mutator()

    def _update_ai(self, dt):
        self.ai_timer -= dt
        incoming = [b for b in self.balls if b.vx > 0]
        if incoming:
            target_ball = min(incoming, key=lambda b: abs(b.x - self.p2.x))
            if self.ai_timer <= 0:
                self.ai_timer = 0.12
                # Adaptive error based on mutator
                err_range = 35.0 if self.current_mutator["id"] in ("SUPERNOVA", "TINY") else 20.0
                self.ai_error = random.uniform(-err_range, err_range)
            self.ai_target_y = target_ball.y + self.ai_error
        else:
            self.ai_target_y = ARENA.centery

        # Smooth glide toward target
        center_y = self.p2.y + self.p2.h / 2
        diff = self.ai_target_y - center_y
        if abs(diff) > 8:
            step = math.copysign(min(abs(diff), PADDLE_SPEED * 0.88 * dt), diff)
            self.p2.move(step, ARENA)


# --- Visual Renderer ---
class Renderer:
    def __init__(self, surface):
        self.surface = surface
        pygame.font.init()
        self.font_lg = pygame.font.SysFont("consolas", 44, bold=True)
        self.font_md = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_sm = pygame.font.SysFont("consolas", 15)

    def draw(self, game):
        # Background
        self.surface.fill(COLOR_BG)

        # Shake effect
        offset_x = random.uniform(-game.screen_shake, game.screen_shake) if game.screen_shake > 0 else 0
        offset_y = random.uniform(-game.screen_shake, game.screen_shake) if game.screen_shake > 0 else 0

        # Arena Bounds
        arena_rect = ARENA.move(offset_x, offset_y)
        pygame.draw.rect(self.surface, COLOR_ARENA_BORDER, arena_rect, 2, border_radius=6)

        # Center Dashed Line
        for y in range(arena_rect.top + 10, arena_rect.bottom - 10, 24):
            pygame.draw.line(self.surface, (30, 36, 52),
                             (arena_rect.centerx, y), (arena_rect.centerx, y + 12), 2)

        # Mutator-specific Arena Elements
        if game.current_mutator["id"] == "GRAVITY":
            # Swirling black hole core
            pygame.draw.circle(self.surface, (60, 25, 90), arena_rect.center, 38)
            pygame.draw.circle(self.surface, (190, 80, 255), arena_rect.center, 28, 2)
            pygame.draw.circle(self.surface, (240, 220, 255), arena_rect.center, 4)

        elif game.current_mutator["id"] == "PORTALS":
            # Twin neon portals
            p1_rect = game.portal1.move(offset_x, offset_y)
            p2_rect = game.portal2.move(offset_x, offset_y)
            pygame.draw.ellipse(self.surface, (20, 100, 120), p1_rect)
            pygame.draw.ellipse(self.surface, (30, 255, 235), p1_rect, 2)
            pygame.draw.ellipse(self.surface, (20, 100, 120), p2_rect)
            pygame.draw.ellipse(self.surface, (30, 255, 235), p2_rect, 2)

        # Top Scoreboard HUD
        s1 = self.font_lg.render(str(game.p1_score), True, COLOR_P1)
        s2 = self.font_lg.render(str(game.p2_score), True, COLOR_P2)
        self.surface.blit(s1, (arena_rect.centerx - 70, 16))
        self.surface.blit(s2, (arena_rect.centerx + 45, 16))

        first_to = self.font_sm.render(f"FIRST TO {SCORE_LIMIT}", True, COLOR_MUTED)
        self.surface.blit(first_to, (arena_rect.centerx - first_to.get_width() // 2, 45))

        # Mode label
        mode_lbl = self.font_sm.render(f"MODE: {game.mode}", True, COLOR_MUTED)
        self.surface.blit(mode_lbl, (arena_rect.left, 45))

        # Active Mutator Banner (HUD bottom)
        mut = game.current_mutator
        tag = self.font_md.render(f"★ ACTIVE RULE: {mut['name']} ★", True, mut["banner_col"])
        desc = self.font_sm.render(mut["desc"], True, COLOR_TEXT)
        self.surface.blit(tag, (arena_rect.centerx - tag.get_width() // 2, arena_rect.bottom + 10))
        self.surface.blit(desc, (arena_rect.centerx - desc.get_width() // 2, arena_rect.bottom + 34))

        # Big Mutator Flash Banner (when point is scored)
        if game.mutator_timer > 0:
            alpha = min(1.0, game.mutator_timer / 0.4)
            banner_bg = pygame.Rect(arena_rect.left + 40, arena_rect.centery - 45, arena_rect.width - 80, 90)
            overlay = pygame.Surface((banner_bg.width, banner_bg.height), pygame.SRCALPHA)
            overlay.fill((10, 12, 20, int(220 * alpha)))
            self.surface.blit(overlay, banner_bg.topleft)
            pygame.draw.rect(self.surface, mut["banner_col"], banner_bg, 2, border_radius=4)

            alert_text = self.font_lg.render(f"MUTATION: {mut['name']}!", True, mut["banner_col"])
            self.surface.blit(alert_text, (banner_bg.centerx - alert_text.get_width() // 2, banner_bg.centery - 22))

        # Paddles
        p1_r = game.p1.rect.move(offset_x, offset_y)
        p2_r = game.p2.rect.move(offset_x, offset_y)
        pygame.draw.rect(self.surface, COLOR_P1, p1_r, border_radius=3)
        pygame.draw.rect(self.surface, COLOR_P2, p2_r, border_radius=3)

        # Balls
        for ball in game.balls:
            bx = ball.x + offset_x
            by = ball.y + offset_y

            # Ghost mutator invisibility near center
            if game.current_mutator["id"] == "GHOST" and abs(bx - arena_rect.centerx) < 140:
                # Ghost ball renders as faint spectral ripple
                pygame.draw.circle(self.surface, (60, 70, 95), (round(bx), round(by)), BALL_RADIUS, 1)
                continue

            # Motion Trail
            for i, (tx, ty) in enumerate(ball.trail):
                trail_r = int(BALL_RADIUS * (i + 1) / len(ball.trail) * 0.7)
                pygame.draw.circle(self.surface, (90, 110, 150), (round(tx), round(ty)), max(1, trail_r))

            # Ball Body
            b_col = mut["banner_col"] if mut["id"] == "SUPERNOVA" else COLOR_BALL
            pygame.draw.circle(self.surface, b_col, (round(bx), round(by)), BALL_RADIUS)

        # Game State Overlays
        if game.state == "MENU":
            self._draw_menu()
        elif game.state == "GAMEOVER":
            self._draw_gameover(game)

    def _draw_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 235))
        self.surface.blit(overlay, (0, 0))

        title = self.font_lg.render("ROULETTE PONG", True, COLOR_MUTATOR)
        sub = self.font_md.render("It's Pong, but every point triggers a wild rule mutation!", True, COLOR_TEXT)
        self.surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 140))
        self.surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 205))

        # Instructions / Choices
        c1 = self.font_md.render("[1] 1 PLAYER (vs AI)", True, COLOR_P1)
        c2 = self.font_md.render("[2] 2 PLAYERS (Local Couch)", True, COLOR_P2)
        controls = self.font_sm.render("Controls: P1 [W/S]  |  P2 [Up/Down]  |  [ESC] Pause/Menu", True, COLOR_MUTED)

        self.surface.blit(c1, (WIDTH // 2 - c1.get_width() // 2, 300))
        self.surface.blit(c2, (WIDTH // 2 - c2.get_width() // 2, 355))
        self.surface.blit(controls, (WIDTH // 2 - controls.get_width() // 2, 450))

    def _draw_gameover(self, game):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 220))
        self.surface.blit(overlay, (0, 0))

        win_color = COLOR_P1 if game.winner == "PLAYER 1" else COLOR_P2
        title = self.font_lg.render(f"{game.winner} WINS!", True, win_color)
        sub = self.font_md.render(f"Final Score: {game.p1_score} - {game.p2_score}", True, COLOR_TEXT)
        prompt = self.font_sm.render("Press [SPACE] or [ENTER] to Play Again  |  [ESC] for Menu", True, COLOR_MUTED)

        self.surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 210))
        self.surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 275))
        self.surface.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 360))


# --- Main Loop ---
def main():
    parser = argparse.ArgumentParser(description="Roulette Pong")
    parser.add_argument("--smoke", action="store_true", help="Run fast automated headless validation")
    args = parser.parse_args()

    if args.smoke:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    pygame.init()
    pygame.display.set_caption("Roulette Pong — 'This, but That'")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    renderer = Renderer(screen)
    game = RoulettePong(mode="1P", sound=not args.smoke)

    if args.smoke:
        # Automated simulation of full game
        game.state = "PLAY"
        for _ in range(600):
            # Simulate both paddles tracking balls
            p1_in = 1 if game.balls and game.balls[0].y > game.p1.y + game.p1.h / 2 else -1
            p2_in = 1 if game.balls and game.balls[0].y > game.p2.y + game.p2.h / 2 else -1
            game.update(1 / 60, p1_in, p2_in)
            renderer.draw(game)
        print("Smoke: Roulette Pong simulated successfully with zero errors.")
        pygame.quit()
        return

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = min(0.05, clock.tick(60) / 1000.0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if game.state == "MENU":
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        game.mode = "1P"
                        game.state = "PLAY"
                        game.reset_match()
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        game.mode = "2P"
                        game.state = "PLAY"
                        game.reset_match()
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif game.state == "PLAY":
                    if event.key == pygame.K_ESCAPE:
                        game.state = "MENU"
                elif game.state == "GAMEOVER":
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        game.state = "PLAY"
                        game.reset_match()
                    elif event.key == pygame.K_ESCAPE:
                        game.state = "MENU"

        # Continuous Input
        keys = pygame.key.get_pressed()
        p1_input = 0.0
        if keys[pygame.K_w]:
            p1_input -= 1.0
        if keys[pygame.K_s]:
            p1_input += 1.0

        p2_input = 0.0
        if keys[pygame.K_UP]:
            p2_input -= 1.0
        if keys[pygame.K_DOWN]:
            p2_input += 1.0

        game.update(dt, p1_input, p2_input)
        renderer.draw(game)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
