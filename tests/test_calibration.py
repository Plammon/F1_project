from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.domain.calibration import build_strategy_calibration_report


class CalibrationTests(unittest.TestCase):
    def test_tuned_reports_match_or_beat_legacy_baseline(self) -> None:
        reports = build_strategy_calibration_report()

        for strategy_name, strategy_reports in reports.items():
            tuned = strategy_reports["tuned"]
            legacy = strategy_reports["legacy"]

            self.assertGreaterEqual(
                tuned.winner_hits,
                legacy.winner_hits,
                msg=f"{strategy_name} winner hits regressed",
            )
            self.assertGreaterEqual(
                tuned.average_podium_overlap,
                legacy.average_podium_overlap,
                msg=f"{strategy_name} podium overlap regressed",
            )
            self.assertLessEqual(
                tuned.average_winner_rank,
                legacy.average_winner_rank,
                msg=f"{strategy_name} winner rank regressed",
            )


if __name__ == "__main__":
    unittest.main()
