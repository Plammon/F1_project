from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.domain.models import PredictionResult
from f1_predictor.presentation.view_models import (
    build_empty_state,
    build_error_state,
    build_loading_state,
    build_result_state,
)


class ViewModelTests(unittest.TestCase):
    def test_empty_state_has_no_rows(self) -> None:
        view_model = build_empty_state()
        self.assertEqual(view_model.source_tone, "neutral")
        self.assertIn("Live data", view_model.context_text)
        self.assertEqual(view_model.table_rows, [])

    def test_loading_state_mentions_strategy(self) -> None:
        view_model = build_loading_state("Balanced")
        self.assertIn("Balanced", view_model.strategy_text)
        self.assertEqual(view_model.source_label, "Preparing data")
        self.assertIn("Calculating confidence", view_model.confidence_label)

    def test_error_state_preserves_message(self) -> None:
        view_model = build_error_state("No supported race data.")
        self.assertEqual(view_model.source_tone, "error")
        self.assertIn("No supported race data.", view_model.error_text)

    def test_result_state_formats_probability_rows(self) -> None:
        result = PredictionResult(
            predicted_winner="Charles Leclerc",
            driver_probabilities={"Charles Leclerc": 21.5, "Max Verstappen": 20.9},
            top_features_or_factors=["Track fit leads this model."],
            strategy_name="Balanced",
            confidence_label="High",
            confidence_reason="Clear separation at the front.",
            score_gap=0.144,
            calibration_notes=("Balanced trims overconfident pace-only forecasts.",),
            actual_podium=("Charles Leclerc", "Max Verstappen", "Lando Norris"),
            data_source="Fixture dataset",
            generated_at=datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
        )

        view_model = build_result_state(result)

        self.assertEqual(view_model.source_tone, "neutral")
        self.assertEqual(view_model.table_rows[0], ("1", "Charles Leclerc", "21.5%"))
        self.assertIn("Balanced", view_model.strategy_text)
        self.assertEqual(view_model.actual_result_rows[0], ("P1", "Charles Leclerc"))
        self.assertEqual(view_model.confidence_tone, "live")
        self.assertIn("Calibrated gap", view_model.context_text)
        self.assertIn("pace-only forecasts", view_model.explanation_text)
        self.assertIn("Strong validation", view_model.actual_result_note)

    def test_result_state_handles_missing_actual_result(self) -> None:
        result = PredictionResult(
            predicted_winner="Max Verstappen",
            driver_probabilities={"Max Verstappen": 33.1, "Lando Norris": 28.2},
            top_features_or_factors=["Qualifying pace dominates this model."],
            strategy_name="Qualifying Bias",
            confidence_label="Medium",
            confidence_reason="Two drivers are fairly close.",
            score_gap=0.052,
            calibration_notes=("Qualifying Bias still values Saturday pace most.",),
            actual_podium=None,
            data_source="FastF1 qualifying snapshot",
            generated_at=datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
        )

        view_model = build_result_state(result)

        self.assertEqual(view_model.actual_result_rows, [])
        self.assertIn("No official podium is available yet", view_model.actual_result_note)


if __name__ == "__main__":
    unittest.main()
