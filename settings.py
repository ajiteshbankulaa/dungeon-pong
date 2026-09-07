"""Shared dimensions and the small visual vocabulary; no initialization side effects."""
import pygame

WIDTH, HEIGHT = 1100, 680
ARENA = pygame.Rect(55, 105, 990, 525)
PLAYER_X, ENEMY_X = 83, 1003
PLAYER_SPEED, PLAYER_H, PADDLE_W = 540.0, 108, 14
BALL_RADIUS, BALL_START_SPEED, BALL_MAX_SPEED = 9, 430.0, 700.0
BLACK, WHITE = (5, 5, 6), (242, 242, 242)
GRAY, DARK_GRAY = (120, 120, 126), (42, 42, 47)
CYAN, RED, GOLD, VIOLET = (45, 246, 255), (255, 55, 90), (255, 224, 80), (210, 90, 255)


def clamp(value, low, high):
    return max(low, min(high, value))


def predict_y(x, y, vx, vy, target_x, bounds=ARENA):
    """Original folded-wall prediction; encounters may deliberately confound it."""
    if abs(vx) < .001 or (target_x - x) / vx <= 0:
        return y
    top, span = bounds.top + BALL_RADIUS, bounds.height - BALL_RADIUS * 2
    folded = (y + vy * (target_x - x) / vx - top) % (2 * span)
    return top + (2 * span - folded if folded > span else folded)
