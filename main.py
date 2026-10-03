"""Mini Git 진입점: `python main.py`."""

import sys

from mini_git.cli import repl

if __name__ == "__main__":
    sys.exit(repl())
