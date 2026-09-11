import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from campaign import STORY, daily_seed, dungeon_for, map_nodes
from game import Game
from save import SaveStore


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "save.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_campaign_opens_and_completes_prologue(self):
        game = Game(self.path, seed=2)
        game.begin_campaign()
        self.assertEqual(game.state, "story")
        self.assertIn(1, game.store.data["seen_story"])
        for _ in range(len(STORY[1]) // 2):
            game.advance_story()
        self.assertEqual(game.state, "play")
        self.assertEqual(game.level_index, 0)

    def test_map_has_five_dungeons_and_locked_nodes(self):
        nodes = map_nodes(3)
        self.assertEqual(len(nodes), 25)
        self.assertTrue(all(n["unlocked"] for n in nodes[:3]))
        self.assertFalse(nodes[3]["unlocked"])
        self.assertEqual(dungeon_for(25)["name"], "THE INFINITE COURT")

    def test_daily_seed_is_stable_and_date_specific(self):
        self.assertEqual(daily_seed(date(2026, 9, 11)), daily_seed(date(2026, 9, 11)))
        self.assertNotEqual(daily_seed(date(2026, 9, 11)), daily_seed(date(2026, 9, 12)))

    def test_new_progress_fields_round_trip(self):
        store = SaveStore(self.path)
        store.data["mastery"] = 9
        store.data["relics"] = ["BANKED OATH"]
        store.data["settings"]["presentation"] = "CLASSIC"
        store.flush()
        restored = SaveStore(self.path)
        self.assertEqual(restored.data["mastery"], 9)
        self.assertEqual(restored.data["relics"], ["BANKED OATH"])
        self.assertEqual(restored.data["settings"]["presentation"], "CLASSIC")

    def test_controller_button_advances_story(self):
        game = Game(self.path)
        game.begin_campaign()
        page = game.story_page
        game.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
        self.assertEqual(game.story_page, page + 2)


if __name__ == "__main__":
    unittest.main()
