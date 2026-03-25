from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.application.controller import PredictionController
from f1_predictor.data.repository import LocalJsonRaceDataRepository
from f1_predictor.domain.models import PredictionInput


class ControllerTests(unittest.TestCase):
    def test_controller_populates_result_metadata(self) -> None:
        controller = PredictionController(LocalJsonRaceDataRepository())
        prediction_input = PredictionInput(
            season="2025",
            grand_prix="Australian Grand Prix",
            selected_strategy="Balanced",
        )

        result = controller.run_prediction(prediction_input)

        self.assertEqual(result.data_source, "Local sample dataset")
        self.assertEqual(result.predicted_winner, "Max Verstappen")
        self.assertTrue(result.generated_at.tzinfo is not None)

    def test_unknown_strategy_raises(self) -> None:
        controller = PredictionController(LocalJsonRaceDataRepository())
        with self.assertRaises(ValueError):
            controller.run_prediction(
                PredictionInput(
                    season="2025",
                    grand_prix="Australian Grand Prix",
                    selected_strategy="Imaginary Strategy",
                )
            )


if __name__ == "__main__":
    unittest.main()

