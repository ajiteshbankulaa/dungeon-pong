"""Restrained pygame presentation; shapes reinforce every accent color."""
import math
import pygame
from levels import POWER_TEXT
from settings import (WIDTH, HEIGHT, ARENA, BALL_RADIUS, BLACK, WHITE, GRAY,
                      DARK_GRAY, CYAN, RED, GOLD, VIOLET, clamp)


class View:
    def __init__(self, screen):
        self.screen = screen
        self.fonts = {s: pygame.font.SysFont("consolas", s, bold=s >= 30) for s in (15, 18, 22, 30, 50, 68)}
        self.buttons = []

    def text(self, text, x, y, size=18, color=WHITE, anchor="center"):
        image = self.fonts[size].render(str(text), True, color)
        self.screen.blit(image, image.get_rect(**{anchor: (x, y)}))

    def line(self, color, start, end, width=1):
        pygame.draw.line(self.screen, color, start, end, width)

    def dashed(self, color, start, end):
        x1, y1 = start
        x2, y2 = end
        distance = max(1, math.hypot(x2 - x1, y2 - y1))
        for i in range(0, int(distance), 20):
            t, u = i / distance, min(1, (i + 9) / distance)
            self.line(color, (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t), (x1 + (x2 - x1) * u, y1 + (y2 - y1) * u))

    def diamond(self, x, y, color, outline=False, radius=7):
        pygame.draw.polygon(self.screen, color, [(x - radius, y), (x, y - radius), (x + radius, y), (x, y + radius)], 2 if outline else 0)

    def draw(self, game):
        self.screen.fill(BLACK)
        self.buttons = []
        if game.state == "menu":
            self.text("A SMALL ARCADE DESCENT", 550, 128, 15, GRAY)
            self.text("DUNGEON PONG", 550, 193, 68)
            self.text("It starts as Pong. It does not stay that way.", 550, 251, 18, GRAY)
            self.draw_buttons(game, 333)
            data = game.store.data
            self.text(f"CONTINUE  {data['continue_level']:02d}     /     BEST  {data['highest_level']:02d}", 550, 600, 15, GRAY)
        elif game.state == "stats":
            self.draw_stats(game)
        elif game.state == "options":
            self.text("OPTIONS", 550, 140, 50)
            self.text("Boss victories unlock cosmetic paddle styles.", 550, 210, color=GRAY)
            self.draw_buttons(game, 290)
        else:
            self.draw_arena(game)
            if game.state != "play":
                shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                shade.fill((5, 5, 6, 232))
                self.screen.blit(shade, (0, 0))
                pygame.draw.rect(self.screen, BLACK, (0, 638, WIDTH, 42))
                titles = {"pause": "PAUSED", "defeat": "DEFEATED", "victory": "STILL PONG.", "cleared": "LEVEL CLEARED", "powerup": "CHOOSE A POWER"}
                self.text(titles.get(game.state, ""), 550, 205, 50)
                if game.state == "powerup":
                    self.text("Small choices. Different ways to survive.", 550, 262, color=GRAY)
                    self.draw_buttons(game, 345, spacing=100, descriptions=True)
                else:
                    checkpoint = game.store.data["checkpoint"]
                    subtitle = f"Checkpoint: level {min(20, checkpoint + 1)}" if checkpoint else "Every fifth level is a checkpoint."
                    if game.state == "cleared":
                        subtitle = f"Next: {game.level_index + 2:02d}   /   HP restored"
                    if game.state == "victory":
                        subtitle = "Twenty encounters. One very different game."
                    self.text(subtitle, 550, 265, color=GRAY)
                    self.draw_buttons(game, 340)
        if game.store.error:
            self.text("SAVE UNAVAILABLE - progress remains in memory", 550, 18, 15, GOLD)

    def draw_buttons(self, game, start, spacing=54, descriptions=False):
        for i, item in enumerate(game.menu_items()):
            y = start + i * spacing
            selected = i == game.selection
            rect = pygame.Rect(270, y - 23, 560, 48 if not descriptions else 78)
            self.buttons.append(rect)
            if selected:
                self.line(CYAN, (rect.left + 5, y - 12), (rect.left + 5, y + 12), 3)
            self.text(item, 550, y, 22, WHITE if selected else GRAY)
            if descriptions:
                self.text(POWER_TEXT[item], 550, y + 30, 15, GRAY)
        self.text("W/S or arrows to choose   /   Enter to confirm", 550, 651, 15, GRAY)

    def draw_stats(self, game):
        self.text("THE DESCENT SO FAR", 550, 85, 30)
        data, stats = game.store.data, game.stats
        rows = [("Highest level", data["highest_level"]), ("Bosses defeated", stats["bosses_defeated"]),
                ("Enemies defeated", stats["enemies_defeated"]), ("Deaths", stats["deaths"]),
                ("Pong returns", stats["returns"]), ("Longest rally", stats["longest_rally"]),
                ("Projectiles dodged", stats["projectiles_dodged"]), ("Projectiles reflected", stats["projectiles_reflected"]),
                ("Abilities used", stats["abilities_used"]), ("Perfect levels", stats["perfect_levels"]),
                ("Time in the dungeon", f"{int(stats['run_time']) // 60}m {int(stats['run_time']) % 60}s")]
        for i, (name, value) in enumerate(rows):
            self.text(name, 300, 155 + i * 34, color=GRAY, anchor="midleft")
            self.text(value, 800, 155 + i * 34, anchor="midright")
        self.draw_buttons(game, 585)

    def draw_arena(self, game):
        rules = game.encounter.rules()
        phase = game.encounter.phase
        final = rules.get("objective") == "final"
        contrast = game.store.data["settings"]["high_contrast"]
        self.text(f"{game.level_index + 1:02d} / 20", 550, 37, 18, GRAY)
        self.text(game.config["name"], 550, 68, 22)
        if not final:
            self.text("HP", ARENA.left, 45, 15, GRAY, "midleft")
            for i in range(3):
                pygame.draw.rect(self.screen, WHITE if i < game.player_hp else DARK_GRAY, (ARENA.left + i * 24, 66, 16, 7))
            remaining = max(0, rules.get("duration", 35) - game.encounter.elapsed)
            label = f"SURVIVE  {remaining:04.1f}" if rules.get("objective") == "survive" else f"ENEMY  {max(0, game.enemy_hp)}"
            self.text(label, ARENA.right, 60, 18, WHITE, "midright")
        if game.config.get("boss"):
            self.text(f"PHASE {phase}", ARENA.right, 85, 15, VIOLET, "midright")
        pygame.draw.rect(self.screen, GRAY if contrast else DARK_GRAY, game.bounds, 1)
        self.dashed(DARK_GRAY, (ARENA.centerx, game.bounds.top + 10), (ARENA.centerx, game.bounds.bottom - 10))
        if rules.get("arena") == "shrinking":
            self.dashed(GRAY, (ARENA.left, ARENA.top + 100), (ARENA.right, ARENA.top + 100))
            self.dashed(GRAY, (ARENA.left, ARENA.bottom - 100), (ARENA.right, ARENA.bottom - 100))
        if rules.get("arena") == "portals":
            for y in (game.bounds.top, game.bounds.bottom):
                self.line(VIOLET, (ARENA.left + 10, y), (ARENA.right - 10, y), 3)
                for x in (ARENA.centerx - 16, ARENA.centerx + 16):
                    self.line(VIOLET, (x - 5, y - 5), (x, y), 2)
                    self.line(VIOLET, (x, y), (x + 5, y - 5), 2)
        if game.invulnerability <= 0 or int(game.invulnerability * 12) % 2 == 0:
            style = game.store.data["selected_cosmetic"]
            pygame.draw.rect(self.screen, WHITE, game.player.rect, 2 if style == "OUTLINE" else 0, border_radius=3)
            if style == "NOTCHED":
                pygame.draw.rect(self.screen, BLACK, (game.player.x + 4, game.player.y - 3, 6, 6))
        if game.config.get("reverse"):
            self.text("YOU", game.player.x, game.bounds.bottom + 15, 15, CYAN)
        if rules.get("objective") == "core":
            rect = pygame.Rect(ARENA.right - 10, game.bounds.centery - 110, 10, 220)
            pygame.draw.rect(self.screen, WHITE if game.encounter.core_open else GOLD, rect, 2 if game.encounter.core_open else 0)
            if game.encounter.core_open:
                self.line(WHITE, (rect.centerx - 8, rect.centery), (rect.centerx + 8, rect.centery), 2)
        else:
            for paddle in game.enemies:
                pygame.draw.rect(self.screen, CYAN if paddle.stun > 0 else WHITE, paddle.rect, border_radius=3)
                if game.encounter.guard > 0:
                    pygame.draw.rect(self.screen, GOLD, paddle.rect.inflate(10, 10), 2, border_radius=4)
        if game.encounter.teleport_warning > 0 and game.enemies:
            ghost = game.enemies[0].rect.copy()
            ghost.centery = round(game.encounter.teleport_y)
            pygame.draw.rect(self.screen, VIOLET, ghost, 1)
        for obstacle in game.obstacles:
            pygame.draw.rect(self.screen, GRAY if obstacle.warning > 0 else WHITE, obstacle.rect, 1 if obstacle.warning > 0 else 2)
            if obstacle.hp > 0:
                self.line(GRAY, obstacle.rect.topleft, obstacle.rect.bottomright)
                if obstacle.hp > 1:
                    self.line(GRAY, obstacle.rect.topright, obstacle.rect.bottomleft)
        for y, blockable in game.encounter.lanes:
            color = GOLD if blockable else RED
            self.dashed(color, (ARENA.left + 15, y), (ARENA.right - 15, y))
            self.diamond(ARENA.centerx, y, color, blockable, 9)
        for projectile in game.projectiles:
            color = CYAN if projectile.reflected else GOLD if projectile.blockable else RED
            self.diamond(projectile.x, projectile.y, color, projectile.blockable, projectile.radius)
            sign = 1 if projectile.vx > 0 else -1
            self.line(color, (projectile.x - sign * 10, projectile.y), (projectile.x - sign * 17, projectile.y))
        for ball in game.balls:
            color = CYAN if ball.charged else WHITE
            if game.store.data["settings"]["effects"]:
                for i, pos in enumerate(ball.trail[::2]):
                    pygame.draw.circle(self.screen, GRAY if contrast else DARK_GRAY, pos, 2 + i)
            if rules.get("mechanic") == "phantom" and ball.vx * game.direction < 0:
                for offset in (-34, 34):
                    y = clamp(ball.y + offset, game.bounds.top + 10, game.bounds.bottom - 10)
                    pygame.draw.circle(self.screen, VIOLET, (ball.x + 18, y), BALL_RADIUS, 1)
            pygame.draw.circle(self.screen, color, (ball.x, ball.y), BALL_RADIUS)
            if ball.delay > 0 or ball.charged or ball.slime:
                pygame.draw.circle(self.screen, CYAN if ball.charged else GRAY, (ball.x, ball.y), BALL_RADIUS + 5, 1)
        for x, y, color, life in game.effects:
            pygame.draw.circle(self.screen, color, (round(x), round(y)), int(6 + (1 - life / .18) * 22), 1)
        self.text("W/S or arrows: move   /   Space: ability   /   Esc: pause", 550, 654, 15, GRAY)
        powers = [f"BLINK {game.cooldown:.1f}s" if p == "BLINK" and game.cooldown > 0 else p for p in sorted(game.powers)]
        self.text("  /  ".join(powers), ARENA.left, 86, 15, CYAN, "midleft")
        if game.intro > 0:
            pygame.draw.rect(self.screen, BLACK, (120, 286, 860, 137))
            self.text(game.config["category"] if phase == 1 else f"PHASE {phase}", 550, 310, 15, VIOLET if game.config.get("boss") else GRAY)
            self.text(game.config["name"] if phase == 1 else game.notice, 550, 350, 30)
            if phase == 1:
                self.text(game.config["hint"], 550, 391, 15)

    def handle_mouse(self, game, event):
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    game.selection = i
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        game.activate()
                    break
