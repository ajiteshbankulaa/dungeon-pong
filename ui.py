"""Restrained pygame presentation; shapes reinforce every accent color."""
import math
import pygame
from levels import POWER_TEXT
from settings import (WIDTH, HEIGHT, ARENA, BALL_RADIUS, BLACK, WHITE, GRAY,
                      DARK_GRAY, CYAN, RED, GOLD, VIOLET, PLAYER_X, ENEMY_X, PADDLE_W,
                      HELL_RED, HOLY_GOLD, OCEAN_BLUE, NIRVANA_TEAL, clamp)


class View:
    def __init__(self, screen):
        self.screen = screen
        self.fonts = {s: pygame.font.SysFont("consolas", s, bold=s >= 30) for s in (15, 16, 17, 18, 20, 22, 30, 38, 50, 68)}
        self.buttons = []

    def get_font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.SysFont("consolas", size, bold=size >= 30)
        return self.fonts[size]

    def text(self, text, x, y, size=18, color=WHITE, anchor="center"):
        image = self.get_font(size).render(str(text), True, color)
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
        elif game.state == "continue":
            self.text("SELECT ENCOUNTER", 550, 95, 38)
            self.text("Start from any unlocked level.", 550, 142, 16, GRAY)
            self.draw_level_select(game)
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
                    subtitle = f"Checkpoint: level {min(25, checkpoint + 1)}" if checkpoint else "Every fifth level is a checkpoint."
                    if game.state == "cleared":
                        subtitle = f"Next: {game.level_index + 2:02d}   /   HP restored"
                    if game.state == "victory":
                        subtitle = "Twenty-five encounters. One very different game."
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

    def draw_level_select(self, game):
        items = game.menu_items()
        if not items:
            return
        level_items = items[:-1]
        num = len(level_items)
        if num <= 6:
            for i, item in enumerate(items):
                y = 205 + i * 54
                selected = i == game.selection
                rect = pygame.Rect(320, y - 22, 460, 44)
                self.buttons.append(rect)
                if selected:
                    self.line(CYAN, (rect.left + 5, y - 10), (rect.left + 5, y + 10), 3)
                self.text(item, 550, y, 20, WHITE if selected else GRAY)
        else:
            half = (num + 1) // 2
            # Dynamically compact spacing when more than 20 levels are unlocked
            spacing = 33 if half > 10 else 38
            start_y = 175 if half > 10 else 190
            rect_h = 28 if half > 10 else 32
            font_sz = 15 if half > 10 else 17

            for i, item in enumerate(level_items):
                col = 0 if i < half else 1
                row = i if col == 0 else i - half
                x = 125 if col == 0 else 575
                y = start_y + row * spacing
                selected = i == game.selection
                rect = pygame.Rect(x, y - rect_h // 2, 400, rect_h)
                self.buttons.append(rect)
                if selected:
                    pygame.draw.rect(self.screen, DARK_GRAY, rect, border_radius=4)
                    pygame.draw.rect(self.screen, CYAN, rect, 1, border_radius=4)
                    self.line(CYAN, (rect.left + 5, y - 7), (rect.left + 5, y + 7), 3)
                else:
                    pygame.draw.rect(self.screen, (18, 18, 22), rect, border_radius=4)
                self.text(item, rect.centerx, y, font_sz, WHITE if selected else GRAY)

            back_idx = len(items) - 1
            back_y = min(615, start_y + half * spacing + 18)
            selected = back_idx == game.selection
            back_rect = pygame.Rect(440, back_y - 16, 220, 32)
            self.buttons.append(back_rect)
            if selected:
                pygame.draw.rect(self.screen, DARK_GRAY, back_rect, border_radius=4)
                pygame.draw.rect(self.screen, CYAN, back_rect, 1, border_radius=4)
            self.text("BACK", 550, back_y, 16, WHITE if selected else GRAY)

        self.text("W/S/A/D or arrows to navigate   /   Enter or Click to select", 550, 652, 15, GRAY)


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
        pygame.draw.rect(self.screen, CYAN if game.chrono_timer > 0 else (GRAY if contrast else DARK_GRAY), game.bounds, 2 if game.chrono_timer > 0 else 1)
        self.dashed(DARK_GRAY, (ARENA.centerx, game.bounds.top + 10), (ARENA.centerx, game.bounds.bottom - 10))

        # Lord 666 demonic pentagram
        if game.config.get("boss") == "lord666":
            cx, cy = ARENA.centerx, ARENA.centery
            r = 85
            star_pts = [(cx + r * math.cos(i * 4 * math.pi / 5 - math.pi / 2),
                         cy + r * math.sin(i * 4 * math.pi / 5 - math.pi / 2)) for i in range(5)]
            for i in range(5):
                pygame.draw.line(self.screen, (75, 18, 18), star_pts[i], star_pts[(i + 1) % 5], 1)
            pygame.draw.circle(self.screen, (60, 15, 15), (cx, cy), r, 1)

        # The Angel sweeping holy light columns
        if getattr(game.encounter, "holy_beam_warning", 0) > 0:
            for col_x in getattr(game.encounter, "holy_columns", ()):
                if game.encounter.holy_beam_warning > 0.35:
                    self.dashed(HOLY_GOLD, (col_x, game.bounds.top), (col_x, game.bounds.bottom))
                else:
                    beam_surf = pygame.Surface((28, game.bounds.height), pygame.SRCALPHA)
                    beam_surf.fill((255, 250, 180, 160))
                    self.screen.blit(beam_surf, (col_x - 14, game.bounds.top))
                    pygame.draw.rect(self.screen, HOLY_GOLD, (col_x - 14, game.bounds.top, 28, game.bounds.height), 2)

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
            p_rect = game.player.rect
            if "AEGIS" in game.powers and game.aegis_shield_ready:
                pygame.draw.rect(self.screen, GOLD, p_rect.inflate(14, 16), 2, border_radius=5)
            if game.player.stun > 0:
                # Stunned player paddle: cyan electric jitter outline
                jitter = (int(game.player.stun * 35) % 3) - 1
                pygame.draw.rect(self.screen, CYAN, p_rect.move(jitter, 0), 2, border_radius=3)
                self.line(CYAN, (p_rect.left - 6, p_rect.centery - 8), (p_rect.left - 2, p_rect.centery + 8), 2)
                self.line(CYAN, (p_rect.right + 2, p_rect.centery - 8), (p_rect.right + 6, p_rect.centery + 8), 2)
            else:
                pygame.draw.rect(self.screen, WHITE, p_rect, 2 if style == "OUTLINE" else 0, border_radius=3)
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

        # Linked cosmic tether between mid-court Warp Rifts
        warp_rifts = [o for o in game.obstacles if o.is_warp_rift]
        if len(warp_rifts) >= 2:
            r1, r2 = warp_rifts[0], warp_rifts[1]
            self.dashed((75, 45, 110), r1.rect.center, r2.rect.center)
            pulse_t = (game.encounter.elapsed * 1.2) % 1.0
            px = r1.rect.centerx + (r2.rect.centerx - r1.rect.centerx) * pulse_t
            py = r1.rect.centery + (r2.rect.centery - r1.rect.centery) * pulse_t
            pygame.draw.circle(self.screen, CYAN, (round(px), round(py)), 3)
            pygame.draw.circle(self.screen, WHITE, (round(px), round(py)), 1)

        for obstacle in game.obstacles:
            if obstacle.acid_timer > 0:
                # Organic acid pool: rounded ellipse with bubbling slime sheen
                alpha = min(1.0, obstacle.acid_timer / 2.0)
                glow_green = (int(50 * alpha), int(255 * alpha), int(110 * alpha))
                dark_green = (int(20 * alpha), int(85 * alpha), int(35 * alpha))
                pygame.draw.ellipse(self.screen, dark_green, obstacle.rect)
                pygame.draw.ellipse(self.screen, glow_green, obstacle.rect, 2)
                bx = obstacle.rect.centerx - 10
                by = obstacle.rect.centery - 2
                pygame.draw.circle(self.screen, glow_green, (bx, by), 3)
                pygame.draw.circle(self.screen, glow_green, (bx + 20, by + 1), 2)
                continue

            if obstacle.is_bone_spire:
                if obstacle.warning > 0:
                    pygame.draw.rect(self.screen, VIOLET, obstacle.rect, 1)
                    self.line(VIOLET, obstacle.rect.topleft, obstacle.rect.bottomright)
                    self.line(VIOLET, obstacle.rect.topright, obstacle.rect.bottomleft)
                else:
                    # Solid ivory bone spire with <<< one-way pass-through chevrons
                    pygame.draw.rect(self.screen, (225, 220, 210), obstacle.rect)
                    pygame.draw.rect(self.screen, WHITE, obstacle.rect, 1)
                    for by in range(obstacle.rect.top + 16, obstacle.rect.bottom, 18):
                        self.line((135, 125, 115), (obstacle.rect.left + 2, by), (obstacle.rect.right - 2, by), 2)
                    for cy in (obstacle.rect.centery - 24, obstacle.rect.centery + 24):
                        cx = obstacle.rect.centerx
                        self.line(VIOLET, (cx + 3, cy - 4), (cx - 3, cy), 2)
                        self.line(VIOLET, (cx - 3, cy), (cx + 3, cy + 4), 2)
                continue

            if obstacle.one_sided:
                # The Mason's fortress wall: stone blocks with <<< one-way chevrons
                pygame.draw.rect(self.screen, (55, 55, 62), obstacle.rect)
                pygame.draw.rect(self.screen, WHITE, obstacle.rect, 2)
                for y_off in range(obstacle.rect.top + 25, obstacle.rect.bottom, 25):
                    self.line((85, 85, 95), (obstacle.rect.left + 2, y_off), (obstacle.rect.right - 2, y_off), 1)
                for cy in (obstacle.rect.centery - 35, obstacle.rect.centery, obstacle.rect.centery + 35):
                    cx = obstacle.rect.centerx
                    self.line(CYAN, (cx + 4, cy - 6), (cx - 4, cy), 2)
                    self.line(CYAN, (cx - 4, cy), (cx + 4, cy + 6), 2)
                continue

            if obstacle.is_warp_rift:
                # Gatekeeper's linked cosmic warp rift wormhole
                idx = warp_rifts.index(obstacle) if obstacle in warp_rifts else 0
                outer_col = VIOLET if idx == 0 else CYAN
                inner_col = CYAN if idx == 0 else VIOLET
                label = "PORTAL I" if idx == 0 else "PORTAL II"

                pygame.draw.ellipse(self.screen, (20, 12, 38), obstacle.rect)
                pygame.draw.ellipse(self.screen, outer_col, obstacle.rect, 2)
                pulse_offset = int(math.sin(game.encounter.elapsed * 3.5 + idx * 3.14) * 3)
                inner_rect = obstacle.rect.inflate(-8 + pulse_offset, -16 + pulse_offset)
                if inner_rect.width > 4 and inner_rect.height > 4:
                    pygame.draw.ellipse(self.screen, inner_col, inner_rect, 1)
                pygame.draw.circle(self.screen, WHITE, obstacle.rect.center, 3)
                self.text(label, obstacle.rect.centerx, obstacle.rect.top - 12, 15, outer_col)
                continue

            if obstacle.is_tractor_beam:
                # Pulsing alien anti-grav field
                pulse_a = int(60 + 40 * math.sin(game.encounter.elapsed * 4))
                field_surf = pygame.Surface((obstacle.rect.width, obstacle.rect.height), pygame.SRCALPHA)
                field_surf.fill((0, 255, 200, pulse_a))
                self.screen.blit(field_surf, obstacle.rect.topleft)
                pygame.draw.rect(self.screen, CYAN, obstacle.rect, 1)
                for cy in range(obstacle.rect.top + 15, obstacle.rect.bottom, 25):
                    self.line(CYAN, (obstacle.rect.centerx - 12, cy), (obstacle.rect.centerx + 12, cy), 1)
                continue

            if obstacle.is_whirlpool:
                # Ocean whirlpool vortex
                pygame.draw.ellipse(self.screen, (10, 40, 75), obstacle.rect)
                pygame.draw.ellipse(self.screen, OCEAN_BLUE, obstacle.rect, 2)
                t_rot = game.encounter.elapsed * 5
                cx, cy = obstacle.rect.centerx, obstacle.rect.centery
                rx, ry = obstacle.rect.width // 3, obstacle.rect.height // 3
                p_spiral = (round(cx + rx * math.cos(t_rot)), round(cy + ry * math.sin(t_rot)))
                pygame.draw.circle(self.screen, CYAN, p_spiral, 3)
                continue

            if obstacle.is_mandala:
                # Nirvana meditating barrier ring
                pygame.draw.ellipse(self.screen, (20, 50, 45), obstacle.rect)
                pygame.draw.ellipse(self.screen, NIRVANA_TEAL, obstacle.rect, 2)
                pygame.draw.circle(self.screen, GOLD, obstacle.rect.center, 4)
                continue

            if obstacle.is_drone:
                # Alien orbiting defense drone
                pygame.draw.circle(self.screen, (20, 30, 45), obstacle.rect.center, 8)
                pygame.draw.circle(self.screen, CYAN, obstacle.rect.center, 8, 2)
                pygame.draw.circle(self.screen, WHITE, obstacle.rect.center, 3)
                continue

            if obstacle.warning > 0:
                pygame.draw.rect(self.screen, GRAY, obstacle.rect, 1)
                self.line(GRAY, obstacle.rect.topleft, obstacle.rect.bottomright)
                self.line(GRAY, obstacle.rect.topright, obstacle.rect.bottomleft)
                continue


            pygame.draw.rect(self.screen, GRAY if obstacle.warning > 0 else WHITE, obstacle.rect,
                             1 if obstacle.warning > 0 else 2)
            if obstacle.hp > 0:
                self.line(GRAY, obstacle.rect.topleft, obstacle.rect.bottomright)
                if obstacle.hp > 1:
                    self.line(GRAY, obstacle.rect.topright, obstacle.rect.bottomleft)

        for y, blockable in game.encounter.lanes:
            color = GOLD if blockable else RED
            self.dashed(color, (ARENA.left + 15, y), (ARENA.right - 15, y))
            self.diamond(ARENA.centerx, y, color, blockable, 9)
        if game.encounter.fan:
            origin_x = game.enemies[0].x if game.enemies else ARENA.right
            for origin_y, vy in game.encounter.fan:
                travel = abs((game.player.x - origin_x) / 300)
                self.dashed(RED, (origin_x, origin_y), (game.player.x, origin_y + vy * travel))

        for projectile in game.projectiles:
            sign = 1 if projectile.vx > 0 else -1
            if projectile.hellfire_skull:
                # Lord 666 demonic screaming skull
                pygame.draw.circle(self.screen, HELL_RED, (round(projectile.x), round(projectile.y)), 9)
                pygame.draw.circle(self.screen, GOLD, (round(projectile.x), round(projectile.y)), 5)
                pygame.draw.circle(self.screen, BLACK, (round(projectile.x - sign * 2), round(projectile.y - 2)), 2)
                pygame.draw.circle(self.screen, BLACK, (round(projectile.x - sign * 2), round(projectile.y + 2)), 2)
                self.line(HELL_RED, (projectile.x, projectile.y), (projectile.x - sign * 18, projectile.y), 3)
                continue
            if projectile.holy_feather:
                # Angel serene radiance arrow
                f_tip = (round(projectile.x), round(projectile.y))
                f_tail1 = (round(projectile.x - sign * 22), round(projectile.y - 4))
                f_tail2 = (round(projectile.x - sign * 22), round(projectile.y + 4))
                pygame.draw.polygon(self.screen, HOLY_GOLD, [f_tip, f_tail1, f_tail2])
                pygame.draw.polygon(self.screen, WHITE, [f_tip, f_tail1, f_tail2], 1)
                continue
            if projectile.bubble:
                # Leviathan abyssal depth bubble
                pygame.draw.circle(self.screen, (20, 80, 130), (round(projectile.x), round(projectile.y)), 8)
                pygame.draw.circle(self.screen, OCEAN_BLUE, (round(projectile.x), round(projectile.y)), 8, 2)
                pygame.draw.circle(self.screen, WHITE, (round(projectile.x - 2), round(projectile.y - 2)), 2)
                continue
            if projectile.hunter_bolt:
                # Rapid crimson sniper beam streak
                self.line((255, 45, 65), (projectile.x, projectile.y), (projectile.x - sign * 38, projectile.y), 4)
                self.line(WHITE, (projectile.x, projectile.y), (projectile.x - sign * 26, projectile.y), 2)
                pygame.draw.circle(self.screen, (255, 65, 85), (round(projectile.x), round(projectile.y)), 5)
                continue
            if projectile.lightning:
                # Zeus electric chain lightning bolt
                p1 = (round(projectile.x), round(projectile.y))
                p2 = (round(projectile.x - sign * 12), round(projectile.y - 5))
                p3 = (round(projectile.x - sign * 20), round(projectile.y + 5))
                p4 = (round(projectile.x - sign * 32), round(projectile.y))
                pygame.draw.lines(self.screen, CYAN, False, [p1, p2, p3, p4], 3)
                pygame.draw.lines(self.screen, WHITE, False, [p1, p2, p3, p4], 1)
                continue
            if projectile.blood_orb:
                pygame.draw.circle(self.screen, (160, 10, 30), (round(projectile.x), round(projectile.y)), 7)
                pygame.draw.circle(self.screen, (255, 50, 70), (round(projectile.x), round(projectile.y)), 4)
                continue
            if projectile.stone_rubble:
                self.diamond(round(projectile.x), round(projectile.y), (160, 160, 170), False, 9)
                continue
            if projectile.soul_ember:
                self.diamond(round(projectile.x), round(projectile.y), VIOLET, True, projectile.radius)
                pygame.draw.circle(self.screen, VIOLET,
                                   (round(projectile.x), round(projectile.y)), projectile.radius + 4, 1)
                continue
            color = CYAN if projectile.reflected else GOLD if projectile.blockable else RED
            self.diamond(round(projectile.x), round(projectile.y), color, projectile.blockable, projectile.radius)
            self.line(color, (projectile.x - sign * 10, projectile.y), (projectile.x - sign * 17, projectile.y))

        for ball in game.balls:
            color = CYAN if ball.charged else WHITE
            if ball.decoy:
                # Stealth phantom decoy: solid white like real ball, subtle 2px violet core dot
                if game.store.data["settings"]["effects"]:
                    for i, pos in enumerate(ball.trail[::2]):
                        pygame.draw.circle(self.screen, (80, 50, 95), pos, 2 + i)
                pygame.draw.circle(self.screen, WHITE, (round(ball.x), round(ball.y)), BALL_RADIUS)
                pygame.draw.circle(self.screen, (190, 130, 240), (round(ball.x), round(ball.y)), 2)
                continue

            if game.store.data["settings"]["effects"]:
                for i, pos in enumerate(ball.trail[::2]):
                    pygame.draw.circle(self.screen, GRAY if contrast else DARK_GRAY, pos, 2 + i)

            # Fireball (INFERNO): Blazing fiery flame corona & tail
            if ball.fireball:
                f_rad = BALL_RADIUS + int(3 + math.sin(game.encounter.elapsed * 12) * 2)
                pygame.draw.circle(self.screen, HELL_RED, (round(ball.x), round(ball.y)), f_rad + 3)
                pygame.draw.circle(self.screen, GOLD, (round(ball.x), round(ball.y)), f_rad)
                self.line(HELL_RED, (ball.x, ball.y), (ball.x - ball.vx * 0.03, ball.y - ball.vy * 0.03), 4)

            # Yin-Yang dual orbiting cosmic pearls (Nirvana)
            if ball.yin_yang:
                yy_rad = 12
                yy_t = game.encounter.elapsed * 6
                p_yin = (round(ball.x + yy_rad * math.cos(yy_t)), round(ball.y + yy_rad * math.sin(yy_t)))
                p_yang = (round(ball.x - yy_rad * math.cos(yy_t)), round(ball.y - yy_rad * math.sin(yy_t)))
                pygame.draw.circle(self.screen, WHITE, p_yin, 4)
                pygame.draw.circle(self.screen, NIRVANA_TEAL, p_yang, 4)

            # Slime Coat on ball: thick pulsating neon green outer membrane + trailing slime drop
            if ball.slime > 0:
                slime_green = (90, 255, 120)
                pygame.draw.circle(self.screen, slime_green, (round(ball.x), round(ball.y)), BALL_RADIUS + 4, 2)
                drop_x = round(ball.x - ball.vx * 0.02)
                drop_y = round(ball.y - ball.vy * 0.02)
                pygame.draw.circle(self.screen, slime_green, (drop_x, drop_y), 3)

            if rules.get("mechanic") == "phantom" and ball.vx * game.direction < 0 and ball.hidden <= 0:
                for offset in (-34, 34):
                    y = clamp(ball.y + offset, game.bounds.top + 10, game.bounds.bottom - 10)
                    pygame.draw.circle(self.screen, VIOLET, (ball.x + 18, y), BALL_RADIUS, 1)

            partial_phase = ball.hidden > 0 and (ball.hidden > ball.hidden_total - .14 or ball.hidden < .14)
            if ball.hidden <= 0:
                pygame.draw.circle(self.screen, color, (round(ball.x), round(ball.y)), BALL_RADIUS)
                if ball.slime > 0:
                    pygame.draw.circle(self.screen, (160, 255, 180), (round(ball.x), round(ball.y)), BALL_RADIUS - 3)
            elif partial_phase:
                pygame.draw.arc(self.screen, VIOLET, (ball.x - BALL_RADIUS, ball.y - BALL_RADIUS,
                                BALL_RADIUS * 2, BALL_RADIUS * 2), .25, 2.35, 2)
                pygame.draw.arc(self.screen, GRAY, (ball.x - BALL_RADIUS, ball.y - BALL_RADIUS,
                                BALL_RADIUS * 2, BALL_RADIUS * 2), 3.4, 5.5, 1)
            if ball.delay > 0 or ball.charged:
                pygame.draw.circle(self.screen, CYAN if ball.charged else GRAY,
                                   (round(ball.x), round(ball.y)), BALL_RADIUS + 5, 1)

        for x, y, color, life in game.effects:
            pygame.draw.circle(self.screen, color, (round(x), round(y)), int(6 + (1 - life / .18) * 22), 1)
        if game.invulnerability > 0 and game.cooldown > 3.1:
            rect = game.player.rect
            pygame.draw.rect(self.screen, CYAN, rect.inflate(16, 14), 2, border_radius=5)
            self.line(CYAN, (rect.centerx - 22, rect.top), (rect.centerx - 22, rect.bottom))
            self.line(CYAN, (rect.centerx + 22, rect.top), (rect.centerx + 22, rect.bottom))
        self.text("W/S: move  /  Space: Blink  /  E or R-Click: Chrono  /  Esc: pause", 550, 654, 15, GRAY)
        powers = []
        for power in sorted(game.powers):
            if power == "BLINK":
                powers.append(f"SPACE: BLINK {'READY' if game.cooldown <= 0 else f'{game.cooldown:.1f}s'}")
            elif power == "CHRONO":
                if game.chrono_timer > 0:
                    powers.append(f"CHRONO ACTIVE {game.chrono_timer:.1f}s")
                else:
                    powers.append(f"E: CHRONO {'READY' if game.chrono_cooldown <= 0 else f'{game.chrono_cooldown:.1f}s'}")
            elif power == "AEGIS":
                powers.append("AEGIS SHIELD [READY]" if game.aegis_shield_ready else f"AEGIS [{game.aegis_timer:.1f}s]")
            elif power == "INFERNO":
                powers.append(f"INFERNO (BANKS {game.inferno_banks}/2)")
            elif power == "TELEKINESIS":
                powers.append("TELEKINESIS [PASSIVE]")
            elif power == "SHOCK":
                charged = any(ball.charged for ball in game.balls)
                powers.append("SHOCK READY" if charged else f"SHOCK {game.return_count % 3}/3")
            else:
                powers.append(f"PASSIVE: {power}")
        self.text("  /  ".join(powers), ARENA.left, 86, 15, CYAN, "midleft")
        if game.encounter.arrow_charge > 0:
            y = round(game.encounter.arrow_target)
            if game.config.get("name") == "THE HUNTER":
                origin_x = ENEMY_X if game.direction == 1 else PLAYER_X + PADDLE_W
                self.line((255, 50, 50), (origin_x, y), (game.player.x, y), 2)
                pygame.draw.circle(self.screen, RED, (round(game.player.x + PADDLE_W // 2), y), 10, 1)
                self.line(RED, (game.player.x - 4, y), (game.player.x + 20, y), 1)
            else:
                self.dashed(GOLD, (game.player.x, y), (game.enemies[0].x if game.enemies else ARENA.right, y))
                self.diamond(ARENA.centerx, y, GOLD, True, 8)

        if game.combat_notice_timer > 0:
            self.text(game.combat_notice, ARENA.centerx, ARENA.top + 24, 15, game.combat_notice_color)
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
