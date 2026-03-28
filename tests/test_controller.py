from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.application.controller import PredictionController
from f1_predictor.data.repository import LocalJsonRaceDataRepository, RaceDataRepository
from f1_predictor.domain.models import DriverFeatures, PredictionInput, RetrievedRaceData


class ControllerTests(unittest.TestCase):
    def test_controller_populates_result_metadata(self) -> None:
        controller = PredictionController(LocalJsonRaceDataRepository())
        prediction_input = PredictionInput(
            season="2025",
            grand_prix="Australian Grand Prix",
            selected_strategy="Balanced",
        )

        result = controller.run_prediction(prediction_input)

        self.assertEqual(result.data_source, "Fixture dataset")
        self.assertEqual(result.predicted_winner, "Max Verstappen")
        self.assertEqual(result.strategy_name, "Balanced")
        self.assertIn(result.confidence_label, {"Low", "Medium", "High"})
        self.assertGreater(result.score_gap, 0.0)
        self.assertTrue(result.calibration_notes)
        self.assertEqual(result.session_label, "Fixture qualifying snapshot")
        self.assertTrue(result.generated_at.tzinfo is not None)

    def test_available_weekends_returns_supported_catalog(self) -> None:
        controller = PredictionController(LocalJsonRaceDataRepository())
        weekends = controller.available_weekends()

        self.assertGreaterEqual(len(weekends), 6)
        self.assertEqual(weekends[0].support_mode, "Fixture data (tests only)")
        self.assertIn(
            "British Grand Prix",
            [weekend.grand_prix for weekend in weekends if weekend.season == "2025"],
        )

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

    def test_controller_builds_historical_comparison_and_adjusts_confidence(self) -> None:
        class StubRepository(RaceDataRepository):
            def get_available_seasons(self) -> list[str]:
                return ["2026"]

            def get_available_grand_prix(self, season: str) -> list[str]:
                return ["British Grand Prix"]

            def get_supported_weekends(self):
                return []

            def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
                return RetrievedRaceData(
                    driver_feature_table={
                        "Lando Norris": DriverFeatures(97, 95, 94, 87, 91),
                        "Max Verstappen": DriverFeatures(96, 94, 92, 86, 88),
                        "Oscar Piastri": DriverFeatures(95, 93, 91, 85, 89),
                    },
                    data_source="FastF1 live qualifying data",
                    session_label="Qualifying session",
                    data_completeness=0.4,
                )

            def get_actual_podium(self, season: str, grand_prix: str):
                return ("Lando Norris", "Oscar Piastri", "Max Verstappen")

        controller = PredictionController(StubRepository())
        result = controller.run_prediction(
            PredictionInput(
                season="2026",
                grand_prix="British Grand Prix",
                selected_strategy="Balanced",
            )
        )

        self.assertIsNotNone(result.historical_comparison)
        self.assertEqual(result.historical_comparison.actual_winner, "Lando Norris")
        self.assertEqual(result.historical_comparison.podium_overlap, 3)
        self.assertEqual(result.confidence_label, "Low")


if __name__ == "__main__":
    unittest.main()
