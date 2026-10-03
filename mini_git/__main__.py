"""`python -m mini_git` 진입점."""

import sys

from mini_git.cli import repl

if __name__ == "__main__":
    sys.exit(repl())
