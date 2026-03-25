"""Application controller for prediction workflows."""

from __future__ import annotations

from dataclasses import replace

from f1_predictor.data.repository import RaceDataRepository
from f1_predictor.domain.models import PredictionInput, PredictionResult
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
        return replace(
            raw_result,
            data_source=retrieved_data.data_source,
            generated_at=prediction_input.generated_at_factory(),
        )
