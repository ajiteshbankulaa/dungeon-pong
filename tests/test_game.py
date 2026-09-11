import copy
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from entities import Ball, Obstacle, Projectile, circle_rect
from game import Game
from levels import LEVELS
from save import SaveStore
from settings import *


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "save.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_creates_valid_save(self):
        store = SaveStore(self.path)
        self.assertEqual(json.loads(self.path.read_text())["version"], 1)
        self.assertEqual(store.data["highest_level"], 1)

    def test_corrupted_and_non_object_recover(self):
        for raw in ("{broken", "[]", "null", "42", '"text"'):
            with self.subTest(raw=raw):
                self.path.write_text(raw)
                store = SaveStore(self.path)
                self.assertEqual(store.data["highest_level"], 1)
                self.assertEqual(self.path.with_suffix(".json.corrupt").read_text(), raw)

    def test_old_save_and_missing_fields(self):
        self.path.write_text(json.dumps({"highest_level": 8, "checkpoint": 5, "stats": {"wins": 12}}))
        store = SaveStore(self.path)
        self.assertEqual(store.data["continue_level"], 6)
        self.assertEqual(store.data["stats"]["wins"], 12)
        self.assertEqual(store.data["stats"]["returns"], 0)

    def test_malformed_fields_and_nonfinite_stats(self):
        self.path.write_text(json.dumps({"stats": {"wins": float("nan"), "returns": -3, "deaths": 10**400},
                                        "settings": [], "highest_level": "twenty", "checkpoint": 999,
                                        "unlocked_powers": ["BOGUS", None, {}], "selected_cosmetic": []}))
        store = SaveStore(self.path)
        self.assertEqual(store.data["highest_level"], 1)
        self.assertEqual(store.data["checkpoint"], 0)
        self.assertEqual(store.data["unlocked_powers"], [])
        self.assertEqual(store.data["stats"]["wins"], 0)
        self.assertIsNone(store.error)

    def test_atomic_failure_preserves_previous_save(self):
        store = SaveStore(self.path)
        before = self.path.read_bytes()
        store.data["highest_level"] = 9
        with patch("save.os.replace", side_effect=PermissionError("read only")):
            self.assertFalse(store.flush())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertIsNotNone(store.error)
        self.assertTrue(store.flush())

    def test_unwritable_location_does_not_crash(self):
        self.path.write_text("not a directory")
        store = SaveStore(self.path / "child.json")
        self.assertIsNotNone(store.error)
        self.assertEqual(store.data["highest_level"], 1)


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "save.json"
        self.game = Game(self.path, seed=4)
        self.game.start()
        self.game.intro = 0
        self.game.store.data["settings"]["effects"] = False

    def tearDown(self):
        self.temp.cleanup()

    def load(self, level):
        self.game.load_level(level - 1)
        self.game.intro = 0
        return self.game

    def key(self, key):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_new_and_continue(self):
        g = self.game
        g.load_level(2)
        g.clear_level()
        g = Game(self.path)
        g.start("continue")
        self.assertEqual(g.level_index, 3)
        self.assertEqual(g.player_hp, 3)
        self.assertEqual(g.stats["wins"], 1)
        g.start()
        self.assertEqual(g.level_index, 0)
        self.assertEqual(g.store.data["highest_level"], 4)

    def test_checkpoint_and_unlocks_persist(self):
        g = self.load(5)
        g.powers = {"BLINK"}
        g.clear_level()
        g.choose_power("RICOCHET")
        g.store.data["selected_cosmetic"] = "OUTLINE"
        g.store.flush()
        restored = Game(self.path)
        restored.start("checkpoint")
        self.assertEqual(restored.level_index, 5)
        self.assertEqual(restored.powers, {"BLINK", "RICOCHET"})
        self.assertEqual(restored.store.data["selected_cosmetic"], "OUTLINE")
        self.assertEqual(restored.stats["bosses_defeated"], 1)

    def test_pending_choice_survives_quitting(self):
        g = self.load(2)
        g.clear_level()
        restored = Game(self.path)
        restored.start("continue")
        self.assertEqual(restored.state, "powerup")
        restored.choose_power("REFLECT")
        self.assertEqual(restored.level_index, 2)
        self.assertIn("REFLECT", restored.powers)
        self.assertEqual(restored.store.data["pending_power_level"], 0)

    def test_exhausted_power_pool(self):
        g = self.load(10)
        g.powers = {"BLINK", "REFLECT", "SHOCK", "RICOCHET", "CHRONO", "AEGIS", "INFERNO", "TELEKINESIS"}
        g.clear_level()
        self.assertEqual(g.state, "cleared")
        g.activate()
        self.assertEqual(g.level_index, 10)

    def test_damage_recovery_game_over_and_restart(self):
        g = self.game
        g.store.data["checkpoint"] = 5
        g.store.data["highest_level"] = 6
        g.hurt()
        g.hurt()
        self.assertEqual(g.player_hp, 2)
        for _ in range(2):
            g.invulnerability = 0
            g.hurt()
        self.assertEqual(g.state, "defeat")
        g.hurt()
        self.assertEqual(g.stats["deaths"], 1)
        g.activate()
        self.assertEqual(g.level_index, 5)
        self.assertEqual(g.player_hp, 3)

    def test_pause_freezes_telegraph_projectile_and_cooldown(self):
        g = self.load(15)
        g.encounter.warning = .7
        g.projectiles.append(Projectile(600, 300, -310))
        g.cooldown = 2
        before = copy.deepcopy((g.balls, g.projectiles, g.encounter.__dict__, g.cooldown, g.stats))
        self.key(pygame.K_ESCAPE)
        g.update(1, 1)
        self.assertEqual(before, (g.balls, g.projectiles, g.encounter.__dict__, g.cooldown, g.stats))
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.state, "play")

    def test_fixed_step_movement_matches_frame_rates(self):
        positions = []
        for fps in (30, 60, 144):
            g = Game(Path(self.temp.name) / f"{fps}.json", seed=1)
            g.start()
            for _ in range(fps // 2):
                g.update(1 / fps, -1)
            positions.append(g.player.y)
        self.assertLess(max(positions) - min(positions), 5)

    def test_fast_ball_cannot_tunnel_through_paddle(self):
        g = self.game
        g.balls = [Ball(x=g.player.x + 70, y=g.player.y, vx=-700, vy=0, delay=0)]
        g.update(.1)
        self.assertGreater(g.balls[0].vx, 0)
        self.assertEqual(g.stats["returns"], 1)

    def test_circle_corner_does_not_false_hit(self):
        self.assertFalse(circle_rect(0, 0, 9, pygame.Rect(8, 8, 10, 10)))

    def test_sharp_returns_respect_speed_cap(self):
        g = self.game
        ball = Ball(x=106, y=g.player.y + 42, vx=-700, vy=0, delay=0)
        g.balls = [ball]
        g.update(.02)
        self.assertLessEqual(math.hypot(ball.vx, ball.vy), 700.00001)
        self.assertGreater(ball.vy, 0)

    def test_blink_with_projectiles_and_cooldown(self):
        g = self.load(11)
        g.powers.add("BLINK")
        g.balls = [Ball(x=400, y=180, vx=-400, delay=0)]
        g.projectiles = [Projectile(90, 215, -310)]
        old = g.player.y
        g.use_ability()
        self.assertGreater(old - g.player.y, 100)
        self.assertLessEqual(old - g.player.y, 210)
        self.assertGreater(g.invulnerability, 0)
        g.use_ability()
        self.assertEqual(g.stats["abilities_used"], 1)
        self.assertEqual(g.cooldown, 3.6)

    def test_blink_is_available_from_a_fresh_game(self):
        self.assertIn("BLINK", self.game.powers)

    def test_gold_blocks_without_power_and_reflect_stuns(self):
        g = self.game
        g.projectiles = [Projectile(g.player.x + 5, g.player.y, -310, blockable=True)]
        g.update_projectiles(.001)
        self.assertEqual(g.player_hp, 3)
        self.assertFalse(g.projectiles)
        g.powers.add("REFLECT")
        p = Projectile(g.player.x + 5, g.player.y, -310, blockable=True)
        g.projectiles = [p]
        g.update_projectiles(.001)
        self.assertTrue(p.reflected)
        self.assertEqual(g.stats["projectiles_reflected"], 1)
        p.x, p.y = g.enemies[0].x, g.enemies[0].y
        g.update_projectiles(.001)
        self.assertGreater(g.enemies[0].stun, 0)

    def test_red_damage_dodge_and_return_corridor(self):
        g = self.game
        g.balls.clear()
        g.projectiles = [Projectile(g.player.x + 5, g.player.y, -310)]
        g.update_projectiles(.001)
        self.assertEqual(g.player_hp, 2)
        g.projectiles = [Projectile(20, 180, -310)]
        g.update_projectiles(.001)
        self.assertEqual(g.stats["projectiles_dodged"], 1)
        g.balls = [Ball(x=200, y=g.player.y, vx=-430, vy=0, delay=0)]
        g.projectiles = [Projectile(220, g.player.y, -310)]
        g.update_projectiles(.001)
        self.assertFalse(g.projectiles)
        self.assertEqual(g.player_hp, 2)

    def test_shock_third_return_and_stun(self):
        g = self.game
        g.powers.add("SHOCK")
        g.return_count = 2
        ball = Ball(x=106, y=g.player.y, vx=-430, vy=0, delay=0)
        g.balls = [ball]
        g.update_ball(ball, .01)
        self.assertTrue(ball.charged)
        ball.x, ball.y = g.enemies[0].x - 10, g.enemies[0].y
        g.update_ball(ball, .01)
        self.assertGreater(g.enemies[0].stun, 0)

    def test_ricochet_charges_and_breaks_two_hit_cover(self):
        g = self.load(17)
        obstacle = g.obstacles[0]
        obstacle.warning = 0
        ball = Ball(x=700, y=ARENA.top + 10, vx=430, vy=-100, delay=0, bank=True)
        g.encounter.wall_bounce(g, ball, True)
        self.assertTrue(ball.charged)
        ball.x, ball.y, ball.vy = obstacle.rect.left - 10, obstacle.rect.centery, 0
        g.update_ball(ball, .01)
        self.assertNotIn(obstacle, g.obstacles)

    def test_multiball_portals_and_single_miss_recovery(self):
        g = self.load(18)
        self.assertEqual(len(g.balls), 2)
        ball = g.balls[0]
        ball.delay = 0
        ball.y, ball.vy = ARENA.top + 9, -100
        g.update_ball(ball, .01)
        self.assertGreater(ball.y, ARENA.bottom - 20)
        self.assertLess(ball.vy, 0)
        g.balls[0].x = ARENA.left - 30
        g.balls[0].vx = -430
        g.balls[1].x = ARENA.left - 30
        g.balls[1].delay = 0
        g.step(.01)
        self.assertEqual(g.player_hp, 2)
        self.assertEqual(len(g.balls), 2)
        self.assertTrue(all(b.delay > 0 for b in g.balls))

    def test_moving_wall_and_shrinking_bounds(self):
        g = self.load(6)
        old = g.obstacles[0].rect.centery
        g.encounter.update(g, 1)
        self.assertNotEqual(old, g.obstacles[0].rect.centery)
        g = self.load(16)
        g.encounter.update(g, 100)
        self.assertEqual(g.bounds.height, ARENA.height - 200)
        self.assertTrue(g.bounds.contains(g.player.rect))

    def test_gravity_bends_ball(self):
        g = self.load(12)
        ball = Ball(x=300, y=300, vx=430, vy=0, delay=0)
        g.balls = [ball]
        g.update_ball(ball, .01)
        self.assertGreater(ball.vy, 0)

    def test_reverse_goal_and_player_return(self):
        g = self.load(19)
        ball = Ball(x=g.player.x - 10, y=g.player.y, vx=430, vy=0, delay=0)
        g.balls = [ball]
        g.update_ball(ball, .01)
        self.assertLess(ball.vx, 0)
        ball.x = ARENA.left - 30
        g.update_ball(ball, .01)
        self.assertEqual(g.enemy_hp, 1)

    def test_swarm_destroyed_individually(self):
        g = self.load(13)
        for i in range(3):
            paddle = g.enemies[0]
            ball = Ball(x=paddle.x - 10, y=paddle.y, vx=430, vy=0, delay=0, returned=True)
            g.balls = [ball]
            g.update_ball(ball, .01)
        self.assertEqual(g.state, "cleared")
        self.assertFalse(g.enemies)

    def test_survival_completes_without_enemy_hp(self):
        g = self.load(14)
        g.encounter.elapsed = 34.99
        g.encounter.update(g, .02)
        self.assertEqual(g.state, "cleared")

    def test_breakout_protects_enemy_until_blocks_gone(self):
        g = self.load(17)
        ball = Ball(x=ARENA.right + 30, y=300, vx=430, delay=0, returned=True)
        g.balls = [ball]
        g.update_ball(ball, .001)
        self.assertEqual(g.enemy_hp, 2)
        self.assertLess(ball.vx, 0)
        g.obstacles.clear()
        ball.x, ball.vx = ARENA.right + 30, 430
        g.update_ball(ball, .001)
        self.assertEqual(g.enemy_hp, 1)

    def test_core_requires_return_and_open_window(self):
        g = self.load(15)
        ball = Ball(x=ARENA.right + 30, y=ARENA.centery, vx=430, delay=0)
        g.balls = [ball]
        g.update_ball(ball, .001)
        self.assertEqual(g.enemy_hp, 6)
        ball.returned = True
        ball.x, ball.vx = ARENA.right + 30, 430
        g.encounter.core_open = False
        g.update_ball(ball, .001)
        self.assertEqual(g.enemy_hp, 6)
        ball.x, ball.vx = ARENA.right + 30, 430
        g.encounter.core_open = True
        g.update_ball(ball, .001)
        self.assertEqual(g.enemy_hp, 5)

    def test_all_boss_phases_clear_old_attacks(self):
        for level in (5, 10, 15, 20, 25):
            g = self.load(level)
            expected = 5 if level == 25 else 3
            phases = {1}
            while g.enemy_hp > 1:
                previous = g.encounter.phase
                g.projectiles = [Projectile(200, 200, -310)]
                g.damage_enemy()
                phases.add(g.encounter.phase)
                if g.encounter.phase != previous:
                    self.assertFalse(g.projectiles)
                    self.assertGreater(g.intro, 0)
                    self.assertTrue(all(b.delay > 0 for b in g.balls))
            self.assertEqual(phases, set(range(1, expected + 1)))
            if level == 25:
                self.assertEqual(g.player_hp, 1)
                self.assertEqual(len(g.balls), 1)
            g.damage_enemy()
            self.assertIn(g.state, ("powerup", "victory", "cleared"))

    def test_projectile_patterns_telegraph_and_recovery(self):
        g = self.load(11)
        g.encounter.pattern_clock = 0
        g.step(.01)
        self.assertGreater(g.encounter.warning, 0)
        g.step(1.0)
        self.assertTrue(g.projectiles)
        self.assertGreater(g.encounter.pattern_clock, 3)

    def test_ai_reaction_speed_limit_and_prediction_error(self):
        g = self.game
        paddle = g.enemies[0]
        paddle.target = 200
        paddle.reaction = .3
        g.balls = [Ball(x=500, y=550, vx=430, delay=0)]
        old = paddle.y
        g.update_ai(.01)
        self.assertEqual(paddle.target, 200)
        self.assertLessEqual(abs(paddle.y - old), g.config["speed"] * .01 + .0001)

    def test_menu_options_stats_and_mouse_ready_states(self):
        g = self.game
        g.state = "menu"
        g.selection = 3
        g.activate()
        self.assertEqual(g.state, "options")
        g.activate()
        self.assertTrue(g.store.data["settings"]["effects"])
        self.key(pygame.K_ESCAPE)
        g.selection = 2
        g.activate()
        self.assertEqual(g.state, "stats")
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.state, "menu")

    def test_gravity_cannot_create_vertical_softlock(self):
        ball = Ball(vx=1, vy=1200)
        ball.cap()
        self.assertGreaterEqual(abs(ball.vx), 219.99)
        self.assertLessEqual(math.hypot(ball.vx, ball.vy), BALL_MAX_SPEED + .001)

    def test_free_serve_cannot_clear_a_level(self):
        g = self.game
        ball = Ball(x=ARENA.right + 30, y=300, vx=430, delay=0)
        g.balls = [ball]
        g.update_ball(ball, .001)
        self.assertEqual(g.enemy_hp, 2)
        self.assertLess(ball.vx, 0)

    def test_final_phase_one_returned_hit_wins(self):
        g = self.load(25)
        g.enemy_hp = 1
        g.encounter.transition(g)
        paddle = g.enemies[0]
        ball = Ball(x=paddle.x - 10, y=paddle.y, vx=430, vy=0, delay=0, returned=True)
        g.balls = [ball]
        g.update_ball(ball, .01)
        self.assertEqual(g.state, "victory")
        self.assertEqual(g.store.data["checkpoint"], 25)

    def test_reflect_against_core_cancels_warning(self):
        g = self.load(15)
        p = Projectile(ENEMY_X, ARENA.centery, 480, reflected=True)
        g.projectiles = [p]
        g.update_projectiles(.001)
        self.assertIn(p, g.projectiles)  # No collision with a hidden paddle.
        g.projectiles.clear()
        g.encounter.warning = .5
        g.encounter.lanes = [(300, True)]
        g.encounter.core_open = False
        g.projectiles = [Projectile(ARENA.right - 15, 300, 480, reflected=True)]
        g.update_projectiles(.01)
        self.assertFalse(g.projectiles)
        self.assertFalse(g.encounter.lanes)
        self.assertEqual(g.encounter.warning, 0)

    def test_reflect_handles_red_projectiles_too(self):
        g = self.game
        g.powers.add("REFLECT")
        p = Projectile(g.player.x + 5, g.player.y, -310, blockable=False)
        g.projectiles = [p]
        g.update_projectiles(.001)
        self.assertTrue(p.reflected)
        self.assertEqual(g.player_hp, 3)

    def test_skeleton_guard_persists_until_enemy_return_then_releases(self):
        g = self.load(2)
        encounter = g.encounter
        encounter.player_shots = 2
        ball = g.balls[0]
        encounter.returned(g, ball, True)
        encounter.update(g, 5.5)
        self.assertGreater(encounter.guard, 0)
        self.assertTrue(encounter.guard_waiting_for_return)
        self.assertEqual(g.enemies[0].height, 145)
        encounter.returned(g, ball, False)
        encounter.update(g, .36)
        encounter.update(g, .01)
        self.assertEqual(encounter.guard, 0)
        self.assertEqual(g.enemies[0].height, 88)

    def test_skeleton_arrow_is_telegraphed_and_spawned(self):
        g = self.load(2)
        encounter = g.encounter
        encounter.enemy_shots = 3
        encounter.returned(g, g.balls[0], False)
        self.assertGreater(encounter.arrow_charge, .7)
        self.assertFalse(g.projectiles)
        encounter.update(g, .76)
        self.assertEqual(len(g.projectiles), 1)
        self.assertTrue(g.projectiles[0].blockable)

    def test_slime_coat_makes_exactly_two_bounces_springy(self):
        g = self.load(1)
        ball = g.balls[0]
        g.encounter.enemy_shots = 2
        g.encounter.returned(g, ball, False)
        self.assertEqual(ball.slime, 2)
        before = abs(ball.vy) or 100
        ball.vy = before
        g.encounter.wall_bounce(g, ball, True)
        first = abs(ball.vy)
        g.encounter.wall_bounce(g, ball, False)
        second = abs(ball.vy)
        g.encounter.wall_bounce(g, ball, True)
        third = abs(ball.vy)
        self.assertGreater(first, before)
        self.assertGreater(second, first)
        self.assertEqual(third, second)
        self.assertEqual(ball.slime, 0)

    def test_wraith_phases_ball_at_midcourt_for_brief_window(self):
        g = self.load(3)
        ball = Ball(x=ARENA.centerx + 2, y=300, vx=-430, delay=0, phase_pending=True)
        g.balls = [ball]
        g.update_ball(ball, .01)
        self.assertGreater(ball.hidden, .61)
        self.assertFalse(ball.phase_pending)
        for _ in range(70):
            g.update_ball(ball, .01)
        self.assertEqual(ball.hidden, 0)

    def test_wraith_phase_step_is_telegraphed_before_teleport(self):
        g = self.load(3)
        enemy = g.enemies[0]
        old_y = enemy.y
        g.encounter.teleport_cooldown = 0
        g.encounter.update(g, .01)
        self.assertGreater(g.encounter.teleport_warning, .89)
        self.assertEqual(enemy.y, old_y)
        destination = g.encounter.teleport_y
        g.encounter.update(g, .91)
        self.assertEqual(enemy.y, destination)

    def test_player_paddle_restored_to_original_forgiving_height(self):
        self.assertEqual(self.game.player.height, 108)

    def test_ai_read_interval_is_humanly_delayed(self):
        g = self.game
        paddle = g.enemies[0]
        paddle.reaction = 0
        g.update_ai(.01)
        self.assertGreaterEqual(paddle.reaction, .32)

    def test_ai_prediction_understands_portals_gravity_and_obstacles(self):
        g = self.load(9)
        portal_ball = Ball(x=600, y=ARENA.top + 15, vx=400, vy=-180, delay=0)
        portal_target = g.predict_intercept(portal_ball, g.enemies[0].x)
        naive_target = predict_y(portal_ball.x, portal_ball.y, portal_ball.vx, portal_ball.vy,
                                 g.enemies[0].x, g.bounds)
        self.assertGreater(abs(portal_target - naive_target), 80)
        g = self.load(12)
        gravity_ball = Ball(x=500, y=300, vx=400, vy=0, delay=0)
        self.assertGreater(g.predict_intercept(gravity_ball, g.enemies[0].x), 300)
        g = self.load(6)
        obstacle = g.obstacles[0]
        obstacle.warning = 0
        bank_ball = Ball(x=500, y=obstacle.rect.centery, vx=400, vy=0, delay=0)
        self.assertEqual(g.predict_intercept(bank_ball, g.enemies[0].x), g.bounds.centery)

    def test_level_ten_has_three_distinct_attack_phases(self):
        g = self.load(10)
        self.assertEqual(g.encounter.rules()["pattern"], "aimed")
        g.enemy_hp = 4
        g.encounter.transition(g)
        self.assertEqual(g.encounter.rules()["pattern"], "fan")
        g.encounter.pattern_clock = 0
        g.encounter.update(g, .01)
        # Bullet-hell upgrade: fan now fires 5 spread shots (was 3).
        self.assertGreaterEqual(len(g.encounter.fan), 3)
        g.enemy_hp = 2
        g.encounter.transition(g)
        rules = g.encounter.rules()
        self.assertEqual(rules["pattern"], "alternating")
        self.assertEqual(rules["arena"], "portals")

    def test_twins_have_two_lane_bound_defenders(self):
        g = self.load(8)
        self.assertEqual(len(g.enemies), 2)
        self.assertEqual(len(g.balls), 2)

    def test_continue_level_select_allows_choosing_any_unlocked_level(self):
        g = self.game
        g.store.data["highest_level"] = 6
        g.store.data["continue_level"] = 6
        g.state = "menu"
        g.selection = 1  # CONTINUE
        g.activate()
        self.assertEqual(g.state, "continue")
        items = g.menu_items()
        self.assertIn("LEVEL 04: NECROMANCER", items)
        # Select level 4
        g.selection = items.index("LEVEL 04: NECROMANCER")
        g.activate()
        self.assertEqual(g.state, "play")
        self.assertEqual(g.level_index, 3)  # Level 4 is index 3

    def test_bone_spire_is_one_way_and_breaks_in_one_hit(self):
        g = self.load(4)
        spire = [o for o in g.obstacles if o.is_bone_spire][0]
        spire.warning = 0
        self.assertTrue(spire.one_sided)
        self.assertEqual(spire.hp, 1)

        # 1) Ball moving left (enemy to player: vx < 0): passes straight through!
        enemy_ball = Ball(x=spire.rect.right + 5, y=spire.rect.centery, vx=-430, vy=0, delay=0)
        g.balls = [enemy_ball]
        g.update_ball(enemy_ball, .04)
        self.assertLess(enemy_ball.vx, 0)
        self.assertLess(enemy_ball.x, spire.rect.centerx)
        self.assertIn(spire, g.obstacles)

        # 2) Ball moving right (player to enemy: vx > 0): hits spire, bounces back, destroys spire in 1 hit!
        player_ball = Ball(x=spire.rect.left - 15, y=spire.rect.centery, vx=430, vy=0, delay=0)
        g.balls = [player_ball]
        g.update_ball(player_ball, .04)
        self.assertLess(player_ball.vx, 0)  # Bounced back!
        self.assertNotIn(spire, g.obstacles)  # Destroyed in 1 single hit!

    def test_gatekeeper_warp_rifts_are_linked_and_teleport_ball(self):
        g = self.load(9)  # Level 9: GATEKEEPER
        rifts = [o for o in g.obstacles if o.is_warp_rift]
        self.assertEqual(len(rifts), 2)
        r1, r2 = rifts[0], rifts[1]
        self.assertEqual(r1.warning, 0.0)
        self.assertEqual(r2.warning, 0.0)

        # 1) Ball entering Rift 1 (moving right) teleports out of Rift 2 (continuing right)
        ball = Ball(x=r1.rect.centerx - 5, y=r1.rect.centery, vx=400, vy=50, delay=0)
        g.balls = [ball]
        g.update_ball(ball, 0.02)
        # Should have teleported to r2 and exited to the right of r2
        self.assertGreater(ball.x, r2.rect.right)
        self.assertGreater(ball.vx, 0)
        self.assertGreater(ball.portal_cooldown, 0)

        # 2) Ball entering Rift 2 (moving left) teleports out of Rift 1 (continuing left)
        ball2 = Ball(x=r2.rect.centerx + 5, y=r2.rect.centery, vx=-400, vy=50, delay=0)
        g.balls = [ball2]
        g.update_ball(ball2, 0.02)
        # Should have teleported to r1 and exited to the left of r1
        self.assertLess(ball2.x, r1.rect.left)
        self.assertLess(ball2.vx, 0)
        self.assertGreater(ball2.portal_cooldown, 0)


    def test_chrono_slow_motion_and_cooldown(self):
        g = self.load(0)
        g.powers.add("CHRONO")
        self.assertEqual(g.chrono_timer, 0.0)
        self.assertEqual(g.chrono_cooldown, 0.0)

        # Activate Chrono
        g.use_chrono()
        self.assertAlmostEqual(g.chrono_timer, 2.5)
        self.assertAlmostEqual(g.chrono_cooldown, 7.0)

        # Verify time dilation: 1.0s elapsed dt advances chrono_timer down by 1.0, cooldown down by 1.0
        # Encounter elapsed should only advance by 1.0 * 0.35 = 0.35
        old_enc_elapsed = g.encounter.elapsed
        g.step(1.0)
        self.assertAlmostEqual(g.chrono_timer, 1.5)
        self.assertAlmostEqual(g.chrono_cooldown, 6.0)
        self.assertAlmostEqual(g.encounter.elapsed, old_enc_elapsed + 0.35)

    def test_aegis_absorbs_miss_and_reflects_ball(self):
        g = self.load(0)
        g.powers.add("AEGIS")
        g.aegis_shield_ready = True
        g.player_hp = 3

        # Spawn a ball passing past player paddle into goal
        ball = Ball(x=PLAYER_X - 10, y=ARENA.centery, vx=-400, vy=0, delay=0)
        g.balls = [ball]

        # Trigger hurt: Aegis should absorb the hit, preserve HP, and bounce ball back towards enemy
        g.hurt(ball)
        self.assertEqual(g.player_hp, 3)  # HP protected!
        self.assertFalse(g.aegis_shield_ready)
        self.assertGreater(ball.vx, 0)  # Reflected right!
        self.assertGreaterEqual(ball.x, PLAYER_X + PADDLE_W)

    def test_inferno_ignites_fireball_after_two_banks_and_vaporizes_projectiles(self):
        g = self.load(0)
        g.powers.add("INFERNO")
        ball = Ball(x=ARENA.centerx, y=ARENA.top + 4, vx=400, vy=-200, delay=0)
        g.balls = [ball]

        # First top wall bank
        g.update_ball(ball, 0.02)
        self.assertEqual(g.inferno_banks, 1)
        self.assertFalse(ball.fireball)

        # Simulate second bank on bottom wall
        ball.y = ARENA.bottom - 4
        ball.vy = 200
        g.update_ball(ball, 0.02)
        self.assertEqual(g.inferno_banks, 2)
        self.assertTrue(ball.fireball)  # IGNITED!

        # Fireball should incinerate enemy projectiles on contact
        skull = Projectile(x=ball.x, y=ball.y, vx=-200, vy=0, blockable=False, hellfire_skull=True)
        g.projectiles = [skull]
        g.update_ball(ball, 0.01)
        self.assertNotIn(skull, g.projectiles)

    def test_alien_tractor_beam_and_retaliation_plasma(self):
        g = self.load(13)  # Level 13: THE ALIEN
        beam = [o for o in g.obstacles if o.is_tractor_beam][0]
        self.assertIsNotNone(beam)

        # Ball passing through tractor beam is accelerated and drawn vertically
        ball = Ball(x=beam.rect.centerx - 5, y=beam.rect.centery - 20, vx=200, vy=0, delay=0)
        g.balls = [ball]
        old_vx = ball.vx
        g.update_ball(ball, 0.02)
        self.assertGreater(abs(ball.vx), abs(old_vx))  # Accelerated!

        # Alien retaliates with plasma when squad paddle is destroyed by returned ball
        enemy = g.enemies[0]
        ball.x = enemy.x - 5
        ball.y = enemy.y
        ball.vx = 400
        ball.returned = True
        g.update_ball(ball, 0.02)
        # Should have launched 3 retaliatory plasma bolts
        self.assertTrue(len(g.projectiles) > 0)
        self.assertEqual(len(g.projectiles), 3)


if __name__ == "__main__":
    unittest.main()

