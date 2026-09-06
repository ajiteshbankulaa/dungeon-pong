"""Deterministic no-power pilot. Diagnostic playtest, not a substitute for humans.

Run: python tests/playtest.py. The pilot moves at normal player speed, predicts
ordinary wall/portal returns, chooses angled shots, and avoids nearby red lanes.
It cannot predict obstacles or gravity perfectly and can legitimately lose.
"""
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import Game
from settings import *


def movement(game):
    incoming = [b for b in game.balls if b.vx * game.direction < 0 and b.delay <= 0]
    ball = min(incoming, key=lambda b: abs((b.x - game.player.x) / b.vx), default=None)
    target = game.bounds.centery
    if ball:
        rules = game.encounter.rules()
        flight = max(0, (game.player.x - ball.x) / ball.vx)
        if rules.get("arena") == "portals":
            span = game.bounds.height - BALL_RADIUS * 2
            target = game.bounds.top + BALL_RADIUS + (ball.y + ball.vy * flight - game.bounds.top - BALL_RADIUS) % span
        else:
            target = predict_y(ball.x, ball.y, ball.vx, ball.vy, game.player.x, game.bounds)
        # Aim alternately with each tip, while keeping the intercept inside the paddle.
        target += 24 * (1 if game.return_count % 2 else -1)
    danger = [p.y for p in game.projectiles if not p.blockable and not p.reflected and abs(p.x - game.player.x) < 650]
    if danger and (ball is None or abs((ball.x - game.player.x) / ball.vx) > .65):
        options = [game.bounds.top + 55 + i * (game.bounds.height - 110) / 20 for i in range(21)]
        safe = [y for y in options if all(abs(y - p) > game.player.height / 2 + 16 for p in danger)]
        if safe:
            target = min(safe, key=lambda y: abs(y - target))
    delta = target - game.player.y
    return 0 if abs(delta) < 5 else 1 if delta > 0 else -1


def main():
    results = []
    with tempfile.TemporaryDirectory() as directory:
        for seed in (3, 11, 29):
            for level in range(1, 21):
                game = Game(Path(directory) / f"{seed}-{level}.json", seed=seed)
                game.load_level(level - 1)
                for frame in range(60 * 240):
                    game.update(1 / 60, movement(game))
                    for ball in game.balls:
                        assert all(math.isfinite(v) for v in (ball.x, ball.y, ball.vx, ball.vy))
                        assert math.hypot(ball.vx, ball.vy) <= BALL_MAX_SPEED + .001
                    assert len(game.balls) <= 2
                    assert len(game.projectiles) <= 8
                    if game.state != "play":
                        break
                results.append({"seed": seed, "level": level, "state": game.state,
                                "seconds": round(frame / 60, 1), "hp": game.player_hp,
                                "enemy_hp": game.enemy_hp, "returns": game.stats["returns"]})
    output = Path(__file__).resolve().parents[1] / "artifacts" / "playtest.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, indent=2))
    for level in range(1, 21):
        runs = [r for r in results if r["level"] == level]
        print(f"{level:02d}: " + " | ".join(f"{r['state']} {r['seconds']}s ({r['returns']} returns)" for r in runs))
    print(f"Diagnostic results: {output}")


if __name__ == "__main__":
    main()
