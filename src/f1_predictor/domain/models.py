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
    session_label: str = "Qualifying"
    data_completeness: float = 1.0
    context_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RaceWeekendOption:
    season: str
    grand_prix: str
    support_mode: str


@dataclass(frozen=True)
class PredictionInput:
    season: str
    grand_prix: str
    selected_strategy: str

    @staticmethod
    def generated_at_factory() -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class HistoricalComparison:
    season: str
    grand_prix: str
    predicted_winner: str
    actual_winner: str
    predicted_top_three: tuple[str, ...]
    actual_podium: tuple[str, str, str]
    winner_match: bool
    podium_overlap: int


@dataclass(frozen=True)
class PredictionResult:
    predicted_winner: str
    driver_probabilities: dict[str, float]
    top_features_or_factors: list[str]
    strategy_name: str
    confidence_label: str = "Medium"
    confidence_reason: str = ""
    actual_podium: tuple[str, str, str] | None = None
    historical_comparison: HistoricalComparison | None = None
    data_source: str = "unknown"
    session_label: str = "Qualifying"
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
