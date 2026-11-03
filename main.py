"""Launch What Returns, a playable poem."""
import argparse
from pathlib import Path
from poem.app import run

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='What Returns')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    run(args.smoke, args.screenshots)
