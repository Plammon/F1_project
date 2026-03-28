from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.application.controller import PredictionController
from f1_predictor.data.repository import LocalJsonRaceDataRepository
from f1_predictor.domain.models import PredictionResult
from f1_predictor.presentation.tk_app import F1PredictorApp


class UISmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        controller = PredictionController(LocalJsonRaceDataRepository())
        self.app = F1PredictorApp(controller)
        self.app.withdraw()

    def tearDown(self) -> None:
        self.app.destroy()

    def test_initial_state_is_user_friendly(self) -> None:
        self.assertIn("Select a Grand Prix", self.app._headline_label.cget("text"))
        self.assertEqual(self.app._run_button.cget("state"), "normal")
        self.assertEqual(self.app._tree.get_children(), ())

    def test_render_result_populates_table(self) -> None:
        result = PredictionResult(
            predicted_winner="Lando Norris",
            driver_probabilities={"Lando Norris": 31.1, "Max Verstappen": 29.7},
            top_features_or_factors=["Recent form strongly shapes this strategy."],
            strategy_name="Balanced",
            confidence_label="Medium",
            confidence_reason="Front-runners remain close.",
            actual_podium=("Max Verstappen", "Lando Norris", "Charles Leclerc"),
            data_source="Fixture dataset",
            generated_at=datetime(2026, 3, 29, 18, 0, tzinfo=timezone.utc),
        )
        self.app.render_result(result)

        self.assertIn("Lando Norris", self.app._headline_label.cget("text"))
        self.assertEqual(len(self.app._tree.get_children()), 2)
        self.assertEqual(self.app._actual_result_rows[0][0].cget("text"), "P1")
        self.assertIn("Max Verstappen", self.app._actual_result_rows[0][1].cget("text"))
        self.assertIn("confidence", self.app._confidence_badge.cget("text").lower())

    def test_error_state_displays_banner(self) -> None:
        self.app._handle_prediction_error("Live data failed.")
        self.assertIn("Live data failed.", self.app._error_var.get())


if __name__ == "__main__":
    unittest.main()
