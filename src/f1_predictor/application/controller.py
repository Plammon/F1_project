"""Application controller for prediction workflows."""

from __future__ import annotations

from dataclasses import replace

from f1_predictor.data.repository import RaceDataRepository
from f1_predictor.domain.models import (
    HistoricalComparison,
    PredictionInput,
    PredictionResult,
    RaceWeekendOption,
)
from f1_predictor.domain.strategies import build_strategy_catalog


class PredictionController:
    """Coordinates the UI, repository, and prediction strategies."""

    def __init__(self, repository: RaceDataRepository) -> None:
        self._repository = repository
        self._strategies = build_strategy_catalog()

    def available_strategies(self) -> list[str]:
        return list(self._strategies.keys())

    def available_seasons(self) -> list[str]:
        return self._repository.get_available_seasons()

    def available_grand_prix(self, season: str) -> list[str]:
        return self._repository.get_available_grand_prix(season)

    def available_weekends(self) -> list[RaceWeekendOption]:
        return self._repository.get_supported_weekends()

    def run_prediction(self, prediction_input: PredictionInput) -> PredictionResult:
        if prediction_input.selected_strategy not in self._strategies:
            raise ValueError(
                f"Unknown strategy: {prediction_input.selected_strategy}"
            )

        retrieved_data = self._repository.get_race_features(
            prediction_input.season,
            prediction_input.grand_prix,
        )
        strategy = self._strategies[prediction_input.selected_strategy]
        raw_result = strategy.predict(retrieved_data.driver_feature_table)
        actual_podium = None
        historical_comparison = None
        get_actual_podium = getattr(self._repository, "get_actual_podium", None)
        if callable(get_actual_podium):
            try:
                actual_podium = get_actual_podium(
                    prediction_input.season,
                    prediction_input.grand_prix,
                )
            except Exception:
                actual_podium = None
        if actual_podium:
            historical_comparison = self._build_historical_comparison(
                prediction_input,
                raw_result,
                actual_podium,
            )
        confidence_label, confidence_reason = self._adjust_confidence(
            raw_result.confidence_label,
            raw_result.confidence_reason,
            retrieved_data.data_completeness,
        )
        return replace(
            raw_result,
            actual_podium=actual_podium,
            historical_comparison=historical_comparison,
            confidence_label=confidence_label,
            confidence_reason=confidence_reason,
            data_source=retrieved_data.data_source,
            session_label=retrieved_data.session_label,
            generated_at=prediction_input.generated_at_factory(),
        )

    def _build_historical_comparison(
        self,
        prediction_input: PredictionInput,
        raw_result: PredictionResult,
        actual_podium: tuple[str, str, str],
    ) -> HistoricalComparison:
        predicted_top_three = tuple(list(raw_result.driver_probabilities.keys())[:3])
        podium_overlap = len(set(predicted_top_three) & set(actual_podium))
        return HistoricalComparison(
            season=prediction_input.season,
            grand_prix=prediction_input.grand_prix,
            predicted_winner=raw_result.predicted_winner,
            actual_winner=actual_podium[0],
            predicted_top_three=predicted_top_three,
            actual_podium=actual_podium,
            winner_match=raw_result.predicted_winner == actual_podium[0],
            podium_overlap=podium_overlap,
        )

    def _adjust_confidence(
        self,
        base_label: str,
        base_reason: str,
        data_completeness: float,
    ) -> tuple[str, str]:
        order = ["Low", "Medium", "High"]
        current_index = order.index(base_label) if base_label in order else 1

        if data_completeness < 0.45:
            current_index = 0
        elif data_completeness < 0.65:
            current_index = max(0, current_index - 1)

        completeness_note = (
            f"Data completeness was {int(data_completeness * 100)}% for recent form and track-history coverage."
        )
        return order[current_index], f"{base_reason} {completeness_note}".strip()
