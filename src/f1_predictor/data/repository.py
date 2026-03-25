"""Repositories for live and mock race data."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from f1_predictor.domain.models import DriverFeatures, RetrievedRaceData
from f1_predictor.paths import resolve_path


class RaceDataRepository(ABC):
    """Abstract repository for race feature retrieval."""

    @abstractmethod
    def get_available_seasons(self) -> list[str]:
        """Return supported seasons."""

    @abstractmethod
    def get_available_grand_prix(self, season: str) -> list[str]:
        """Return race weekends for a season."""

    @abstractmethod
    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        """Return driver features for the given weekend."""


class LocalJsonRaceDataRepository(RaceDataRepository):
    """Uses bundled mock data to keep the demo reliable."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or resolve_path("data", "sample_race_data.json")
        with self.data_path.open("r", encoding="utf-8") as handle:
            self._raw_data = json.load(handle)

    def get_available_seasons(self) -> list[str]:
        return sorted(self._raw_data.keys())

    def get_available_grand_prix(self, season: str) -> list[str]:
        if season not in self._raw_data:
            raise ValueError(f"Unknown season: {season}")
        return sorted(self._raw_data[season].keys())

    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        try:
            raw_features = self._raw_data[season][grand_prix]["driver_features"]
        except KeyError as exc:
            raise ValueError(
                f"Missing race data for {season} {grand_prix}"
            ) from exc

        table = {
            driver: DriverFeatures(**metrics)
            for driver, metrics in raw_features.items()
        }
        return RetrievedRaceData(
            driver_feature_table=table,
            data_source="Local sample dataset",
        )


class FastF1RaceDataRepository(RaceDataRepository):
    """Optional live repository backed by FastF1."""

    def __init__(self) -> None:
        try:
            import fastf1  # type: ignore
        except ImportError:
            fastf1 = None
        self._fastf1 = fastf1

    def _require_fastf1(self):
        if self._fastf1 is None:
            raise RuntimeError("FastF1 is not installed in this environment.")
        return self._fastf1

    def get_available_seasons(self) -> list[str]:
        return ["2025", "2026"]

    def get_available_grand_prix(self, season: str) -> list[str]:
        fastf1 = self._require_fastf1()
        schedule = fastf1.get_event_schedule(int(season), include_testing=False)
        return sorted(schedule["EventName"].tolist())

    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        fastf1 = self._require_fastf1()
        event = fastf1.get_event(int(season), grand_prix)
        session = fastf1.get_session(int(season), event["EventName"], "Q")
        session.load(laps=False, telemetry=False, weather=False, messages=False)

        results = session.results.head(5)
        if results.empty:
            raise RuntimeError("FastF1 returned no qualifying data.")

        feature_table = {}
        for _, row in results.iterrows():
            abbrev = row["Abbreviation"]
            position = float(row["Position"])
            qualifying_score = max(60.0, 101.0 - position * 4.5)
            feature_table[abbrev] = DriverFeatures(
                qualifying_score=qualifying_score,
                recent_form=max(65.0, qualifying_score - 2.0),
                track_fit=max(65.0, qualifying_score - 4.0),
                pit_efficiency=82.0,
                reliability=88.0,
            )

        return RetrievedRaceData(
            driver_feature_table=feature_table,
            data_source="FastF1 qualifying snapshot",
        )


class ResilientRaceDataRepository(RaceDataRepository):
    """Wraps a live repository with a reliable local fallback."""

    def __init__(
        self,
        primary: RaceDataRepository,
        fallback: RaceDataRepository,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def get_available_seasons(self) -> list[str]:
        try:
            return self.primary.get_available_seasons()
        except Exception:
            return self.fallback.get_available_seasons()

    def get_available_grand_prix(self, season: str) -> list[str]:
        try:
            return self.primary.get_available_grand_prix(season)
        except Exception:
            return self.fallback.get_available_grand_prix(season)

    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        try:
            return self.primary.get_race_features(season, grand_prix)
        except Exception as primary_exc:
            try:
                return self.fallback.get_race_features(season, grand_prix)
            except Exception as fallback_exc:
                fallback_options = []
                try:
                    fallback_options = self.fallback.get_available_grand_prix(season)
                except Exception:
                    fallback_options = []

                guidance = ""
                if fallback_options:
                    guidance = (
                        " Available sample races for this season: "
                        + ", ".join(fallback_options)
                        + "."
                    )

                raise RuntimeError(
                    "Live data could not be loaded and no local fallback data exists "
                    f"for {season} {grand_prix}. "
                    f"Live error: {primary_exc}. "
                    f"Fallback error: {fallback_exc}."
                    + guidance
                ) from fallback_exc
