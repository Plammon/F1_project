"""Convenience launcher for running the app without editable install."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.__main__ import main  # noqa: E402


if __name__ == "__main__":
    main()

