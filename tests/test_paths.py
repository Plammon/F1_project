from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.paths import resolve_path


class PathTests(unittest.TestCase):
    def test_resolve_path_finds_existing_data_file(self) -> None:
        resolved = resolve_path("data", "sample_race_data.json")
        self.assertTrue(resolved.exists())
        self.assertEqual(resolved.name, "sample_race_data.json")

    def test_resolve_path_works_with_frozen_flags(self) -> None:
        fake_executable = ROOT / "dist" / "F1Predictor" / "F1Predictor.exe"
        fake_bundle = ROOT
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "executable", str(fake_executable)
        ), patch.object(sys, "_MEIPASS", str(fake_bundle), create=True):
            resolved = resolve_path("data", "sample_race_data.json")
        self.assertTrue(resolved.exists())


if __name__ == "__main__":
    unittest.main()
