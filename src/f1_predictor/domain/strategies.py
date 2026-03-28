"""Strategy pattern implementation for race predictions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from math import exp

from f1_predictor.domain.models import DriverFeatureTable, PredictionResult


class PredictionStrategy(ABC):
    """Interface for interchangeable race-prediction algorithms."""

    name: str
    weights: dict[str, float]
    factor_labels = {
        "qualifying_score": "Qualifying pace",
        "recent_form": "Recent form",
        "track_fit": "Track fit",
        "pit_efficiency": "Pit stop execution",
        "reliability": "Reliability",
    }

    @abstractmethod
    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        """Return winner odds for the provided drivers."""

    def _build_result(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        normalized_scores = self._normalize_driver_scores(driver_feature_table)
        softmax_scores = {
            driver: exp(score * 4.0) for driver, score in normalized_scores.items()
        }
        total = sum(softmax_scores.values()) or 1.0
        ordered_scores = sorted(
            softmax_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        probabilities = {
            driver: round(score / total * 100, 1)
            for driver, score in ordered_scores
        }
        predicted_winner = ordered_scores[0][0]
        confidence_label, confidence_reason = self._build_confidence(
            normalized_scores,
            driver_feature_table,
        )
        top_features = [
            self._build_factor_explanation(label, weight)
            for label, weight in sorted(
                self.weights.items(), key=lambda item: item[1], reverse=True
            )[:3]
        ]
        return PredictionResult(
            predicted_winner=predicted_winner,
            driver_probabilities=probabilities,
            top_features_or_factors=top_features,
            strategy_name=self.name,
            confidence_label=confidence_label,
            confidence_reason=confidence_reason,
        )

    def _normalize_driver_scores(
        self,
        driver_feature_table: DriverFeatureTable,
    ) -> dict[str, float]:
        feature_bounds: dict[str, tuple[float, float]] = {}
        for field_name in self.weights:
            values = [
                getattr(features, field_name)
                for features in driver_feature_table.values()
            ]
            feature_bounds[field_name] = (min(values), max(values))

        normalized_scores: dict[str, float] = {}
        for driver, features in driver_feature_table.items():
            weighted_score = 0.0
            for field_name, weight in self.weights.items():
                lower, upper = feature_bounds[field_name]
                value = getattr(features, field_name)
                normalized = 1.0 if upper == lower else (value - lower) / (upper - lower)
                weighted_score += normalized * weight
            normalized_scores[driver] = weighted_score
        return normalized_scores

    def _build_confidence(
        self,
        normalized_scores: dict[str, float],
        driver_feature_table: DriverFeatureTable,
    ) -> tuple[str, str]:
        ordered = sorted(
            normalized_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        margin = ordered[0][1] - ordered[1][1] if len(ordered) > 1 else 1.0
        driver_count = len(driver_feature_table)
        if margin >= 0.16:
            return (
                "High",
                "The leading driver separated clearly from the rest of the field in this model.",
            )
        if margin >= 0.08:
            return (
                "Medium",
                f"The forecast has a visible leader, but {driver_count} drivers are still reasonably close.",
            )
        return (
            "Low",
            "The front-runners are tightly grouped, so a small pace swing could change the order.",
        )

    def _build_factor_explanation(self, label: str, weight: float) -> str:
        readable = self.factor_labels.get(label, label.replace("_", " ").title())
        emphasis = round(weight * 100)
        return (
            f"{readable} carries about {emphasis}% of the {self.name.lower()} model, "
            "so it strongly shapes the final ranking."
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
