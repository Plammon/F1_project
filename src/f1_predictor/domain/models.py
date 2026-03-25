"""Core domain models for the predictor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DriverFeatures:
    qualifying_score: float
    recent_form: float
    track_fit: float
    pit_efficiency: float
    reliability: float


DriverFeatureTable = dict[str, DriverFeatures]


@dataclass(frozen=True)
class RetrievedRaceData:
    driver_feature_table: DriverFeatureTable
    data_source: str


@dataclass(frozen=True)
class PredictionInput:
    season: str
    grand_prix: str
    selected_strategy: str

    @staticmethod
    def generated_at_factory() -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PredictionResult:
    predicted_winner: str
    driver_probabilities: dict[str, float]
    top_features_or_factors: list[str]
    data_source: str = "unknown"
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

