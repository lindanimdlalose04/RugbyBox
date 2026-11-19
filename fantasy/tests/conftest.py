"""Make the project's own modules importable from the tests.

Tests for the shared store reader live in shared/tests, at the repository
root, because both projects use it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
