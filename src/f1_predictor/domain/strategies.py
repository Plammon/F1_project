"""Strategy pattern implementation for race predictions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from f1_predictor.domain.models import DriverFeatureTable, PredictionResult


class PredictionStrategy(ABC):
    """Interface for interchangeable race-prediction algorithms."""

    name: str
    weights: dict[str, float]

    @abstractmethod
    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        """Return winner odds for the provided drivers."""

    def _build_result(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        raw_scores: dict[str, float] = {}
        for driver, features in driver_feature_table.items():
            weighted_score = 0.0
            for field_name, weight in self.weights.items():
                weighted_score += getattr(features, field_name) * weight
            raw_scores[driver] = weighted_score

        total = sum(raw_scores.values())
        probabilities = {
            driver: round(score / total * 100, 1)
            for driver, score in sorted(
                raw_scores.items(), key=lambda item: item[1], reverse=True
            )
        }
        predicted_winner = next(iter(probabilities))
        top_features = [
            f"{label.replace('_', ' ').title()} drives the {self.name.lower()} model."
            for label, _ in sorted(
                self.weights.items(), key=lambda item: item[1], reverse=True
            )[:3]
        ]
        return PredictionResult(
            predicted_winner=predicted_winner,
            driver_probabilities=probabilities,
            top_features_or_factors=top_features,
        )


class BalancedStrategy(PredictionStrategy):
    name = "Balanced"
    weights = {
        "qualifying_score": 0.30,
        "recent_form": 0.25,
        "track_fit": 0.20,
        "pit_efficiency": 0.10,
        "reliability": 0.15,
    }

    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        return self._build_result(driver_feature_table)


class QualifyingBiasStrategy(PredictionStrategy):
    name = "Qualifying Bias"
    weights = {
        "qualifying_score": 0.45,
        "recent_form": 0.20,
        "track_fit": 0.15,
        "pit_efficiency": 0.05,
        "reliability": 0.15,
    }

    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        return self._build_result(driver_feature_table)


class ConsistencyBiasStrategy(PredictionStrategy):
    name = "Consistency Bias"
    weights = {
        "qualifying_score": 0.15,
        "recent_form": 0.25,
        "track_fit": 0.15,
        "pit_efficiency": 0.10,
        "reliability": 0.35,
    }

    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        return self._build_result(driver_feature_table)


def build_strategy_catalog() -> dict[str, PredictionStrategy]:
    return {
        "Balanced": BalancedStrategy(),
        "Qualifying Bias": QualifyingBiasStrategy(),
        "Consistency Bias": ConsistencyBiasStrategy(),
    }

