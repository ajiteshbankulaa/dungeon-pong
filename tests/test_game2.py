"""
Unit and integration tests for game2.py (Roulette Pong).
Tests game rules, mutator cycle, physics, paddle scaling, scoring, AI, and gameover states.
"""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
from game2 import RoulettePong, MUTATORS, Ball, Paddle, ARENA, SCORE_LIMIT, DEFAULT_PADDLE_H


class RoulettePongTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game = RoulettePong(mode="1P", sound=False)
        self.game.state = "PLAY"
        self.game.serve_delay = 0.0

    def test_initial_state_and_mutators_registered(self):
        self.assertEqual(len(MUTATORS), 10)
        self.assertEqual(self.game.p1_score, 0)
        self.assertEqual(self.game.p2_score, 0)
        self.assertIsNone(self.game.winner)
        self.assertGreaterEqual(len(self.game.balls), 1)

    def test_scoring_increments_and_cycles_mutator(self):
        old_mut = self.game.current_mutator["id"]
        # Position ball out of bounds to the right (Player 1 scores!)
        ball = self.game.balls[0]
        ball.x = ARENA.right + 10
        ball.vx = 400

        self.game.update(0.016, 0.0, 0.0)
        self.assertEqual(self.game.p1_score, 1)
        self.assertEqual(self.game.p2_score, 0)
        self.assertNotEqual(self.game.current_mutator["id"], old_mut)
        self.assertGreater(self.game.mutator_timer, 0.0)

    def test_multiball_mutator_serves_three_balls(self):
        multi_mut = [m for m in MUTATORS if m["id"] == "MULTIBALL"][0]
        self.game.apply_mutator(multi_mut)
        self.assertEqual(len(self.game.balls), 3)

    def test_paddle_scaling_mutators(self):
        tiny_mut = [m for m in MUTATORS if m["id"] == "TINY"][0]
        self.game.apply_mutator(tiny_mut)
        self.assertAlmostEqual(self.game.p1.h, DEFAULT_PADDLE_H * 0.45)
        self.assertAlmostEqual(self.game.p2.h, DEFAULT_PADDLE_H * 0.45)

        titan_mut = [m for m in MUTATORS if m["id"] == "TITAN"][0]
        self.game.apply_mutator(titan_mut)
        self.assertAlmostEqual(self.game.p1.h, DEFAULT_PADDLE_H * 1.60)
        self.assertAlmostEqual(self.game.p2.h, DEFAULT_PADDLE_H * 1.60)

    def test_supernova_speed_multiplication(self):
        nova_mut = [m for m in MUTATORS if m["id"] == "SUPERNOVA"][0]
        self.game.apply_mutator(nova_mut)
        for ball in self.game.balls:
            speed = (ball.vx ** 2 + ball.vy ** 2) ** 0.5
            self.assertGreater(speed, 600.0)

    def test_gravity_mutator_curves_ball_towards_singularity(self):
        grav_mut = [m for m in MUTATORS if m["id"] == "GRAVITY"][0]
        self.game.apply_mutator(grav_mut)
        self.game.serve_delay = 0.0
        ball = Ball(ARENA.centerx - 100, ARENA.centery - 60, 200, 0)
        self.game.balls = [ball]

        # In gravity well, ball vy should accelerate downwards toward center
        self.game.update(0.05, 0.0, 0.0)
        self.assertGreater(ball.vy, 0.0)

    def test_portal_warp_teleports_ball(self):
        portal_mut = [m for m in MUTATORS if m["id"] == "PORTALS"][0]
        self.game.apply_mutator(portal_mut)
        self.game.serve_delay = 0.0
        ball = Ball(self.game.portal1.centerx, self.game.portal1.centery, 300, 0)
        self.game.balls = [ball]

        self.game.update(0.016, 0.0, 0.0)
        self.assertAlmostEqual(ball.x, self.game.portal2.centerx, delta=10)
        self.assertAlmostEqual(ball.y, self.game.portal2.centery, delta=10)
        self.assertGreater(ball.portal_cd, 0.0)

    def test_gameover_triggered_at_score_limit(self):
        self.game.p1_score = SCORE_LIMIT - 1
        ball = self.game.balls[0]
        ball.x = ARENA.right + 20
        ball.vx = 400

        self.game.update(0.016, 0.0, 0.0)
        self.assertEqual(self.game.p1_score, SCORE_LIMIT)
        self.assertEqual(self.game.state, "GAMEOVER")
        self.assertEqual(self.game.winner, "PLAYER 1")

    def test_2p_local_couch_mode(self):
        two_p_game = RoulettePong(mode="2P", sound=False)
        two_p_game.state = "PLAY"
        old_p1_y = two_p_game.p1.y
        old_p2_y = two_p_game.p2.y

        # P1 moves down (+1), P2 moves up (-1)
        two_p_game.update(0.05, 1.0, -1.0)
        self.assertGreater(two_p_game.p1.y, old_p1_y)
        self.assertLess(two_p_game.p2.y, old_p2_y)


if __name__ == "__main__":
    unittest.main()
