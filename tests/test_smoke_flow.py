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


class SmokeFlowTests(unittest.TestCase):
    def test_prediction_flow_returns_ranked_driver_table(self) -> None:
        controller = PredictionController(LocalJsonRaceDataRepository())
        result = controller.run_prediction(
            PredictionInput(
                season="2026",
                grand_prix="Italian Grand Prix",
                selected_strategy="Qualifying Bias",
            )
        )

        self.assertGreaterEqual(len(result.driver_probabilities), 5)
        self.assertEqual(next(iter(result.driver_probabilities)), result.predicted_winner)


if __name__ == "__main__":
    unittest.main()

