"""Internal helpers for strategy calibration and regression checks."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

from f1_predictor.domain.models import DriverFeatureTable, DriverFeatures
from f1_predictor.domain.strategies import (
    BalancedStrategy,
    ConsistencyBiasStrategy,
    PredictionStrategy,
    QualifyingBiasStrategy,
)


@dataclass(frozen=True)
class CalibrationCase:
    name: str
    driver_feature_table: DriverFeatureTable
    actual_winner: str
    actual_podium: tuple[str, str, str]


@dataclass(frozen=True)
class CalibrationReport:
    strategy_name: str
    winner_hits: int
    average_podium_overlap: float
    average_winner_rank: float


def build_calibration_cases() -> dict[str, tuple[CalibrationCase, ...]]:
    return {
        "Balanced": (
            CalibrationCase(
                name="balanced_reliability_check",
                driver_feature_table={
                    "Driver A": DriverFeatures(98, 88, 90, 84, 72),
                    "Driver B": DriverFeatures(94, 95, 93, 86, 94),
                    "Driver C": DriverFeatures(92, 91, 90, 85, 89),
                },
                actual_winner="Driver B",
                actual_podium=("Driver B", "Driver C", "Driver A"),
            ),
            CalibrationCase(
                name="balanced_track_alignment",
                driver_feature_table={
                    "Driver A": DriverFeatures(95, 92, 91, 83, 90),
                    "Driver B": DriverFeatures(93, 94, 96, 84, 92),
                    "Driver C": DriverFeatures(90, 90, 88, 82, 89),
                },
                actual_winner="Driver B",
                actual_podium=("Driver B", "Driver A", "Driver C"),
            ),
        ),
        "Qualifying Bias": (
            CalibrationCase(
                name="qualifying_pole_advantage",
                driver_feature_table={
                    "Driver A": DriverFeatures(99, 89, 94, 81, 86),
                    "Driver B": DriverFeatures(95, 95, 91, 84, 92),
                    "Driver C": DriverFeatures(92, 91, 90, 83, 90),
                },
                actual_winner="Driver A",
                actual_podium=("Driver A", "Driver B", "Driver C"),
            ),
            CalibrationCase(
                name="qualifying_fragility_penalty",
                driver_feature_table={
                    "Driver A": DriverFeatures(99, 88, 93, 80, 69),
                    "Driver B": DriverFeatures(96, 94, 92, 85, 92),
                    "Driver C": DriverFeatures(93, 91, 90, 84, 89),
                },
                actual_winner="Driver B",
                actual_podium=("Driver B", "Driver C", "Driver A"),
            ),
        ),
        "Consistency Bias": (
            CalibrationCase(
                name="consistency_fragile_fast_driver",
                driver_feature_table={
                    "Fast But Fragile": DriverFeatures(99, 92, 91, 84, 70),
                    "Consistent Driver": DriverFeatures(93, 95, 92, 85, 97),
                    "Steady Driver": DriverFeatures(91, 91, 90, 84, 93),
                },
                actual_winner="Consistent Driver",
                actual_podium=("Consistent Driver", "Steady Driver", "Fast But Fragile"),
            ),
            CalibrationCase(
                name="consistency_recent_form_support",
                driver_feature_table={
                    "Driver A": DriverFeatures(94, 91, 89, 83, 82),
                    "Driver B": DriverFeatures(91, 96, 92, 84, 95),
                    "Driver C": DriverFeatures(90, 90, 88, 82, 91),
                },
                actual_winner="Driver B",
                actual_podium=("Driver B", "Driver A", "Driver C"),
            ),
        ),
    }


def build_strategy_calibration_report() -> dict[str, dict[str, CalibrationReport]]:
    cases = build_calibration_cases()
    strategies: dict[str, PredictionStrategy] = {
        "Balanced": BalancedStrategy(),
        "Qualifying Bias": QualifyingBiasStrategy(),
        "Consistency Bias": ConsistencyBiasStrategy(),
    }
    reports: dict[str, dict[str, CalibrationReport]] = {}
    for strategy_name, strategy in strategies.items():
        strategy_cases = cases[strategy_name]
        reports[strategy_name] = {
            "tuned": evaluate_strategy(strategy, strategy_cases),
            "legacy": evaluate_legacy_strategy(strategy, strategy_cases),
        }
    return reports


def evaluate_strategy(
    strategy: PredictionStrategy,
    cases: tuple[CalibrationCase, ...],
) -> CalibrationReport:
    winner_hits = 0
    podium_overlap_total = 0
    winner_rank_total = 0

    for case in cases:
        result = strategy.predict(case.driver_feature_table)
        ordered_drivers = list(result.driver_probabilities.keys())
        winner_hits += int(result.predicted_winner == case.actual_winner)
        podium_overlap_total += len(set(ordered_drivers[:3]) & set(case.actual_podium))
        winner_rank_total += ordered_drivers.index(case.actual_winner) + 1

    total_cases = len(cases)
    return CalibrationReport(
        strategy_name=strategy.name,
        winner_hits=winner_hits,
        average_podium_overlap=round(podium_overlap_total / total_cases, 2),
        average_winner_rank=round(winner_rank_total / total_cases, 2),
    )


def evaluate_legacy_strategy(
    strategy: PredictionStrategy,
    cases: tuple[CalibrationCase, ...],
) -> CalibrationReport:
    winner_hits = 0
    podium_overlap_total = 0
    winner_rank_total = 0

    for case in cases:
        ordered_drivers = _legacy_rank(case.driver_feature_table, strategy.weights)
        winner_hits += int(ordered_drivers[0] == case.actual_winner)
        podium_overlap_total += len(set(ordered_drivers[:3]) & set(case.actual_podium))
        winner_rank_total += ordered_drivers.index(case.actual_winner) + 1

    total_cases = len(cases)
    return CalibrationReport(
        strategy_name=f"{strategy.name} legacy baseline",
        winner_hits=winner_hits,
        average_podium_overlap=round(podium_overlap_total / total_cases, 2),
        average_winner_rank=round(winner_rank_total / total_cases, 2),
    )


def _legacy_rank(
    driver_feature_table: DriverFeatureTable,
    weights: dict[str, float],
) -> list[str]:
    feature_bounds: dict[str, tuple[float, float]] = {}
    for field_name in weights:
        values = [
            getattr(features, field_name)
            for features in driver_feature_table.values()
        ]
        feature_bounds[field_name] = (min(values), max(values))

    raw_scores: dict[str, float] = {}
    for driver, features in driver_feature_table.items():
        raw_scores[driver] = sum(
            _normalize(getattr(features, field_name), feature_bounds[field_name]) * weight
            for field_name, weight in weights.items()
        )

    legacy_scores = {
        driver: exp(score * 4.0)
        for driver, score in raw_scores.items()
    }
    return [
        driver
        for driver, _ in sorted(
            legacy_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def _normalize(value: float, bounds: tuple[float, float]) -> float:
    lower, upper = bounds
    if upper == lower:
        return 1.0
    return (value - lower) / (upper - lower)
