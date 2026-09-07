import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from game import Game
from ui import View
from entities import Projectile
from settings import *


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_all_levels_phases_menus_and_cosmetics_render(self):
        output = Path(__file__).resolve().parents[1] / "artifacts"
        output.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as directory:
            game = Game(Path(directory) / "save.json", seed=2)
            view = View(self.surface)
            thumbnails = []
            for level in range(20):
                game.load_level(level)
                game.intro = 0
                view.draw(game)
                thumbnails.append(pygame.transform.smoothscale(self.surface, (330, 204)))
                if game.config.get("boss"):
                    while game.enemy_hp > 1:
                        game.damage_enemy()
                        game.intro = 0
                        game.encounter.elapsed = 5
                        game.encounter.pattern_clock = .01
                        game.encounter.update(game, .02)
                        view.draw(game)
                        pygame.image.save(self.surface, output / f"boss-{level+1}-phase-{game.encounter.phase}.png")
            sheet = pygame.Surface((330 * 4, 204 * 5))
            for i, thumb in enumerate(thumbnails):
                sheet.blit(thumb, ((i % 4) * 330, (i // 4) * 204))
            pygame.image.save(sheet, output / "encounters.png")
            game.load_level(14)
            game.intro = 0
            game.powers = {"BLINK", "REFLECT", "SHOCK", "RICOCHET"}
            game.cooldown = 3
            game.encounter.phase = 2
            game.encounter.pattern_clock = 0
            game.encounter.update(game, .01)
            view.draw(game)
            pygame.image.save(self.surface, output / "bullet-telegraph.png")
            game.encounter.update(game, .86)
            for p in game.projectiles:
                p.x = 650
            view.draw(game)
            pygame.image.save(self.surface, output / "bullet-pattern.png")
            for style in ("SOLID", "OUTLINE", "NOTCHED"):
                game.store.data["selected_cosmetic"] = style
                view.draw(game)
            for state in ("menu", "pause", "defeat", "victory", "stats", "options", "cleared", "powerup"):
                game.state = state
                game.power_choices = ["BLINK", "REFLECT"]
                view.draw(game)
                pygame.image.save(self.surface, output / f"{state}.png")
                for rect in view.buttons:
                    self.assertTrue(self.surface.get_rect().contains(rect))
            game.load_level(2)
            game.intro = 0
            ball = game.balls[0]
            ball.delay = 0
            ball.x, ball.y = ARENA.centerx - 70, ARENA.centery
            ball.hidden_total = .62
            for label, hidden in (("fade-out", .56), ("invisible", .31), ("fade-in", .08)):
                ball.hidden = hidden
                view.draw(game)
                pygame.image.save(self.surface, output / f"wraith-{label}.png")
            game.encounter.teleport_y = ARENA.top + 110
            game.encounter.teleport_warning = .9
            view.draw(game)
            pygame.image.save(self.surface, output / "wraith-phase-step.png")
            game.load_level(9)
            game.intro = 0
            game.encounter.phase = 2
            game.encounter.pattern_clock = 0
            game.encounter.update(game, .01)
            view.draw(game)
            pygame.image.save(self.surface, output / "phantom-queen-fan-tell.png")
            game.encounter.fan.clear()
            game.balls[0].delay = 0
            game.balls[0].x = 360
            game.balls[0].y = ARENA.top + 80
            game.balls[0].vx = -430
            game.use_ability()
            view.draw(game)
            pygame.image.save(self.surface, output / "blink-emergency.png")

    def test_mouse_activates_menu_item(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(Path(directory) / "save.json")
            view = View(self.surface)
            view.draw(game)
            view.handle_mouse(game, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=view.buttons[0].center))
            self.assertEqual(game.state, "play")
