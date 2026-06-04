"""Entry point: python -m tools.cli <verb> [args]"""

import sys

from tools.cli import main

if __name__ == "__main__":
    sys.exit(main())
