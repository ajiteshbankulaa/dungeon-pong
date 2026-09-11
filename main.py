"""Run with python main.py; --smoke renders using a temporary save."""
import argparse
import os
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Dungeon Pong")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.smoke:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    from audio import Audio
    from game import Game
    from ui import View
    from settings import WIDTH, HEIGHT
    pygame.init()
    pygame.display.set_caption("Dungeon Pong")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    view = View(screen)
    if args.smoke:
        with tempfile.TemporaryDirectory() as directory:
            game = Game(Path(directory) / "save.json", seed=7)
            # No audio in smoke mode (SDL_AUDIODRIVER=dummy).
            if args.screenshots:
                args.screenshots.mkdir(parents=True, exist_ok=True)
                view.draw(game)
                pygame.image.save(screen, args.screenshots / "menu.png")
            from levels import LEVELS
            for level in range(len(LEVELS)):
                game.load_level(level)
                game.intro = 0
                for _ in range(180):
                    game.update(1 / 60)
                view.draw(game)
                if args.screenshots:
                    pygame.image.save(screen, args.screenshots / f"level-{level + 1:02d}.png")
            print(f"Smoke: all {len(LEVELS)} encounters simulated and rendered.")
        pygame.quit()
        return
    game = Game()
    # Create audio engine; respect the saved sound toggle.
    sound_enabled = game.store.data["settings"].get("sound", True)
    game.audio = Audio(enabled=sound_enabled)
    game.audio.set_sfx_volume(game.store.data["settings"].get("sfx_volume", 8) / 10)
    game.audio.start_music(game.store.data["settings"].get("music_volume", 7) / 35)
    clock = pygame.time.Clock()
    try:
        while game.state != "quit":
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.WINDOWFOCUSLOST and game.state == "play":
                    game.state, game.selection = "pause", 0
                view.handle_mouse(game, event)
                game.handle_event(event)
            keys = pygame.key.get_pressed()
            movement = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
            if pygame.joystick.get_count():
                pad = pygame.joystick.Joystick(0)
                axis = pad.get_axis(1)
                if abs(axis) > .18:
                    movement = axis
            game.update(dt, movement)
            view.draw(game)
            pygame.display.flip()
    finally:
        game.store.flush()
        pygame.quit()


if __name__ == "__main__":
    main()
