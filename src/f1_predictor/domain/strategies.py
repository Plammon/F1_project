"""Strategy pattern implementation for race predictions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from math import exp

from f1_predictor.domain.models import DriverFeatureTable, PredictionResult


class PredictionStrategy(ABC):
    """Interface for interchangeable race-prediction algorithms."""

    name: str
    weights: dict[str, float]
    temperature: float
    disagreement_penalty: float
    recovery_bonus: float
    consistency_bonus: float
    track_bonus: float
    calibration_summary: str

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
        normalized_table = self._normalize_feature_table(driver_feature_table)
        raw_scores = self._build_raw_scores(normalized_table)
        calibrated_scores = self._apply_calibration(
            raw_scores,
            driver_feature_table,
            normalized_table,
        )
        probabilities = self._convert_scores_to_probabilities(calibrated_scores)
        predicted_winner = next(iter(probabilities))
        score_gap = self._score_gap(calibrated_scores)
        confidence_label, confidence_reason = self._build_confidence(
            calibrated_scores,
            driver_feature_table,
        )
        top_features = self._build_explanations(
            driver_feature_table,
            normalized_table,
            predicted_winner,
        )
        return PredictionResult(
            predicted_winner=predicted_winner,
            driver_probabilities=probabilities,
            top_features_or_factors=top_features,
            strategy_name=self.name,
            confidence_label=confidence_label,
            confidence_reason=confidence_reason,
            score_gap=score_gap,
            calibration_notes=(self.calibration_summary,),
        )

    def _normalize_feature_table(
        self,
        driver_feature_table: DriverFeatureTable,
    ) -> dict[str, dict[str, float]]:
        feature_bounds: dict[str, tuple[float, float]] = {}
        for field_name in self.weights:
            values = [
                getattr(features, field_name)
                for features in driver_feature_table.values()
            ]
            feature_bounds[field_name] = (min(values), max(values))

        normalized_table: dict[str, dict[str, float]] = {}
        for driver, features in driver_feature_table.items():
            normalized_table[driver] = {}
            for field_name in self.weights:
                lower, upper = feature_bounds[field_name]
                value = getattr(features, field_name)
                normalized = 1.0 if upper == lower else (value - lower) / (upper - lower)
                normalized_table[driver][field_name] = normalized
        return normalized_table

    def _build_raw_scores(
        self,
        normalized_table: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        raw_scores: dict[str, float] = {}
        for driver, normalized_features in normalized_table.items():
            raw_scores[driver] = sum(
                normalized_features[field_name] * weight
                for field_name, weight in self.weights.items()
            )
        return raw_scores

    def _apply_calibration(
        self,
        raw_scores: dict[str, float],
        driver_feature_table: DriverFeatureTable,
        normalized_table: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        calibrated_scores: dict[str, float] = {}
        for driver, raw_score in raw_scores.items():
            features = driver_feature_table[driver]
            normalized_features = normalized_table[driver]

            fragility_gap = max(
                0.0,
                normalized_features["qualifying_score"] - normalized_features["reliability"],
            )
            recovery_gap = max(
                0.0,
                normalized_features["recent_form"] - normalized_features["qualifying_score"],
            )
            consistency_alignment = 1.0 - abs(
                normalized_features["recent_form"] - normalized_features["reliability"]
            )
            track_alignment = 1.0 - abs(
                normalized_features["track_fit"] - normalized_features["qualifying_score"]
            )
            low_reliability_risk = max(0.0, (80.0 - features.reliability) / 100.0)

            calibrated_scores[driver] = (
                raw_score
                - fragility_gap * self.disagreement_penalty
                - low_reliability_risk * (self.disagreement_penalty * 0.6)
                + recovery_gap * self.recovery_bonus
                + consistency_alignment * self.consistency_bonus
                + track_alignment * self.track_bonus
            )
        return calibrated_scores

    def _convert_scores_to_probabilities(
        self,
        calibrated_scores: dict[str, float],
    ) -> dict[str, float]:
        softmax_scores = {
            driver: exp(score * self.temperature)
            for driver, score in calibrated_scores.items()
        }
        total = sum(softmax_scores.values()) or 1.0
        ordered_scores = sorted(
            softmax_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        raw_probabilities = [
            (driver, score / total * 100.0)
            for driver, score in ordered_scores
        ]
        probabilities = {
            driver: round(probability, 1)
            for driver, probability in raw_probabilities
        }

        rounded_total = round(sum(probabilities.values()), 1)
        if raw_probabilities and rounded_total != 100.0:
            top_driver = raw_probabilities[0][0]
            probabilities[top_driver] = round(
                probabilities[top_driver] + (100.0 - rounded_total),
                1,
            )
        return probabilities

    def _score_gap(self, calibrated_scores: dict[str, float]) -> float:
        ordered_scores = sorted(calibrated_scores.values(), reverse=True)
        if len(ordered_scores) < 2:
            return 1.0
        return round(ordered_scores[0] - ordered_scores[1], 3)

    def _build_confidence(
        self,
        calibrated_scores: dict[str, float],
        driver_feature_table: DriverFeatureTable,
    ) -> tuple[str, str]:
        ordered = sorted(
            calibrated_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        score_gap = ordered[0][1] - ordered[1][1] if len(ordered) > 1 else 1.0
        predicted_winner = ordered[0][0]
        winner_features = driver_feature_table[predicted_winner]

        disagreement = max(
            0.0,
            (winner_features.qualifying_score - winner_features.reliability) / 100.0,
        ) + abs(
            winner_features.recent_form - winner_features.qualifying_score
        ) / 180.0

        if score_gap >= 0.12 and disagreement < 0.12:
            return (
                "High",
                "The top driver has a clear calibrated edge and no major reliability-form disagreement.",
            )
        if score_gap >= 0.06 and disagreement < 0.22:
            return (
                "Medium",
                "The forecast has a visible leader, but the front runners are still close or slightly unbalanced.",
            )
        if disagreement >= 0.22:
            return (
                "Low",
                "The leader shows a noticeable pace-versus-reliability mismatch, so the forecast stays cautious.",
            )
        return (
            "Low",
            "The front-runners remain tightly grouped after calibration, so the order can still swing.",
        )

    def _build_explanations(
        self,
        driver_feature_table: DriverFeatureTable,
        normalized_table: dict[str, dict[str, float]],
        predicted_winner: str,
    ) -> list[str]:
        top_weighted_features = sorted(
            self.weights.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:2]
        explanations = [
            self._build_factor_explanation(label, weight)
            for label, weight in top_weighted_features
        ]
        explanations.append(
            self._build_calibration_explanation(
                driver_feature_table[predicted_winner],
                normalized_table[predicted_winner],
            )
        )
        return explanations

    def _build_factor_explanation(self, label: str, weight: float) -> str:
        readable = self.factor_labels.get(label, label.replace("_", " ").title())
        emphasis = round(weight * 100)
        return (
            f"{readable} still carries about {emphasis}% of the {self.name.lower()} model, "
            "so it remains one of the biggest drivers in the final ranking."
        )

    def _build_calibration_explanation(
        self,
        features,
        normalized_features: dict[str, float],
    ) -> str:
        fragility_gap = max(
            0.0,
            normalized_features["qualifying_score"] - normalized_features["reliability"],
        )
        if fragility_gap >= 0.2:
            return (
                "Calibration reduced some of the leader's qualifying-only upside because reliability lags behind the raw pace profile."
            )
        if normalized_features["recent_form"] > normalized_features["qualifying_score"]:
            return (
                "Calibration gave extra credit to recent race form, which helped stabilize the final order."
            )
        return (
            "Calibration rewarded drivers whose pace, form, and reliability point in the same direction."
        )


class BalancedStrategy(PredictionStrategy):
    name = "Balanced"
    weights = {
        "qualifying_score": 0.28,
        "recent_form": 0.27,
        "track_fit": 0.19,
        "pit_efficiency": 0.10,
        "reliability": 0.16,
    }
    temperature = 4.6
    disagreement_penalty = 0.10
    recovery_bonus = 0.05
    consistency_bonus = 0.04
    track_bonus = 0.03
    calibration_summary = (
        "Balanced trims overconfident pace-only forecasts and rewards drivers whose form, reliability, "
        "and track fit agree with each other."
    )

    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        return self._build_result(driver_feature_table)


class QualifyingBiasStrategy(PredictionStrategy):
    name = "Qualifying Bias"
    weights = {
        "qualifying_score": 0.42,
        "recent_form": 0.20,
        "track_fit": 0.18,
        "pit_efficiency": 0.05,
        "reliability": 0.15,
    }
    temperature = 5.2
    disagreement_penalty = 0.18
    recovery_bonus = 0.03
    consistency_bonus = 0.02
    track_bonus = 0.08
    calibration_summary = (
        "Qualifying Bias still values Saturday pace most, but it now pulls back when a pole-like profile "
        "looks fragile over a full race distance."
    )

    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        return self._build_result(driver_feature_table)


class ConsistencyBiasStrategy(PredictionStrategy):
    name = "Consistency Bias"
    weights = {
        "qualifying_score": 0.14,
        "recent_form": 0.27,
        "track_fit": 0.15,
        "pit_efficiency": 0.10,
        "reliability": 0.34,
    }
    temperature = 4.4
    disagreement_penalty = 0.24
    recovery_bonus = 0.07
    consistency_bonus = 0.09
    track_bonus = 0.02
    calibration_summary = (
        "Consistency Bias now penalizes fragile high-pace profiles more aggressively and promotes drivers "
        "whose recent form and reliability stay aligned."
    )

    def predict(self, driver_feature_table: DriverFeatureTable) -> PredictionResult:
        return self._build_result(driver_feature_table)


def build_strategy_catalog() -> dict[str, PredictionStrategy]:
    return {
        "Balanced": BalancedStrategy(),
        "Qualifying Bias": QualifyingBiasStrategy(),
        "Consistency Bias": ConsistencyBiasStrategy(),
    }
