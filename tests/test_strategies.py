from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.domain.models import DriverFeatures
from f1_predictor.domain.strategies import (
    BalancedStrategy,
    ConsistencyBiasStrategy,
    QualifyingBiasStrategy,
)


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feature_table = {
            "Driver A": DriverFeatures(96, 94, 93, 86, 90),
            "Driver B": DriverFeatures(91, 89, 88, 84, 87),
            "Driver C": DriverFeatures(88, 86, 87, 83, 84),
        }

    def test_balanced_strategy_returns_ranked_probabilities(self) -> None:
        result = BalancedStrategy().predict(self.feature_table)
        self.assertEqual(result.predicted_winner, "Driver A")
        self.assertEqual(result.strategy_name, "Balanced")
        self.assertIn(result.confidence_label, {"Low", "Medium", "High"})
        self.assertGreater(result.score_gap, 0.0)
        self.assertTrue(result.calibration_notes)
        self.assertAlmostEqual(sum(result.driver_probabilities.values()), 100.0, places=1)

    def test_qualifying_bias_favors_strong_qualifier(self) -> None:
        result = QualifyingBiasStrategy().predict(self.feature_table)
        self.assertEqual(result.predicted_winner, "Driver A")
        self.assertIn("Qualifying pace", result.top_features_or_factors[0])

    def test_consistency_bias_prefers_reliability(self) -> None:
        feature_table = {
            "Fast But Fragile": DriverFeatures(99, 92, 91, 84, 70),
            "Consistent Driver": DriverFeatures(93, 92, 90, 85, 96),
        }
        result = ConsistencyBiasStrategy().predict(feature_table)
        self.assertEqual(result.predicted_winner, "Consistent Driver")

    def test_confidence_drops_when_front_runners_are_close(self) -> None:
        close_feature_table = {
            "Driver A": DriverFeatures(95, 94, 92, 85, 88),
            "Driver B": DriverFeatures(95, 94, 92, 85, 88),
            "Driver C": DriverFeatures(94.8, 93.9, 91.9, 84.9, 88),
        }
        result = BalancedStrategy().predict(close_feature_table)
        self.assertEqual(result.confidence_label, "Low")


if __name__ == "__main__":
    unittest.main()
