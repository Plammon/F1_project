"""Repositories for live race data and internal test fixtures."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from f1_predictor.domain.models import DriverFeatures, RaceWeekendOption, RetrievedRaceData
from f1_predictor.paths import resolve_path

logger = logging.getLogger(__name__)


class RaceDataRepository(ABC):
    """Abstract repository for race feature retrieval."""

    @abstractmethod
    def get_available_seasons(self) -> list[str]:
        """Return supported seasons."""

    @abstractmethod
    def get_available_grand_prix(self, season: str) -> list[str]:
        """Return race weekends for a season."""

    @abstractmethod
    def get_supported_weekends(self) -> list[RaceWeekendOption]:
        """Return weekend options that the UI can safely show."""

    @abstractmethod
    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        """Return driver features for the given weekend."""


class LocalJsonRaceDataRepository(RaceDataRepository):
    """Internal fixture repository retained for tests and offline development."""

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

    def get_supported_weekends(self) -> list[RaceWeekendOption]:
        weekends: list[RaceWeekendOption] = []
        for season in self.get_available_seasons():
            for grand_prix in self.get_available_grand_prix(season):
                support_mode = self._raw_data[season][grand_prix].get(
                    "support_mode",
                    "Fixture data (tests only)",
                )
                if "fallback" in support_mode.lower():
                    support_mode = "Fixture data (tests only)"
                weekends.append(
                    RaceWeekendOption(
                        season=season,
                        grand_prix=grand_prix,
                        support_mode=support_mode,
                    )
                )
        return weekends

    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        try:
            raw_features = self._raw_data[season][grand_prix]["driver_features"]
        except KeyError as exc:
            raise ValueError(
                f"Missing fixture race data for {season} {grand_prix}"
            ) from exc

        table = {
            driver: DriverFeatures(**metrics)
            for driver, metrics in raw_features.items()
        }
        return RetrievedRaceData(
            driver_feature_table=table,
            data_source="Fixture dataset",
            session_label="Fixture qualifying snapshot",
            data_completeness=0.9,
            context_notes=("Internal test fixture data",),
        )


class FastF1RaceDataRepository(RaceDataRepository):
    """Live repository backed by FastF1."""

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
        schedule = self._load_schedule(int(season))
        return sorted(schedule["EventName"].tolist())

    def get_supported_weekends(self) -> list[RaceWeekendOption]:
        weekends: list[RaceWeekendOption] = []
        for season in self.get_available_seasons():
            try:
                schedule = self._load_schedule(int(season))
            except Exception as exc:
                logger.warning("Could not load FastF1 schedule for %s: %s", season, exc)
                continue

            for _, event in schedule.iterrows():
                weekends.append(
                    RaceWeekendOption(
                        season=season,
                        grand_prix=str(event["EventName"]),
                        support_mode=self._support_mode_for_event(event),
                    )
                )
        return weekends

    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        fastf1 = self._require_fastf1()
        season_int = int(season)
        try:
            event = fastf1.get_event(season_int, grand_prix)
            session = fastf1.get_session(season_int, event["EventName"], "Q")
            session.load(laps=False, telemetry=False, weather=False, messages=False)
        except Exception as exc:
            raise RuntimeError(
                "We do not have enough live qualifying data for this race weekend right now. "
                "Please try another Grand Prix or try again later."
            ) from exc

        results = session.results.copy()
        if results.empty:
            raise RuntimeError(
                "We do not have enough qualifying data for this race weekend yet."
            )

        results = results.dropna(subset=["Position"]).sort_values("Position")
        current_round = int(event["RoundNumber"])
        recent_context, loaded_recent_races = self._load_recent_race_context(
            season_int,
            current_round,
        )
        prior_track_positions = self._load_previous_track_history(season_int, grand_prix)

        best_times = self._collect_best_qualifying_times(results)
        if not best_times:
            raise RuntimeError(
                "Live qualifying timing is incomplete for this weekend. Please try again later."
            )
        pole_time = min(best_times.values())

        feature_table = {}
        for _, row in results.iterrows():
            driver_name = self._driver_name(row)
            qualifying_score = self._build_qualifying_score(
                row,
                best_times.get(driver_name),
                pole_time,
            )
            history = recent_context.get(driver_name, [])
            recent_form = self._build_recent_form(qualifying_score, history)
            reliability = self._build_reliability(qualifying_score, history)
            pit_efficiency = self._build_pit_efficiency(qualifying_score, history)
            track_fit = self._build_track_fit(
                driver_name,
                qualifying_score,
                recent_form,
                prior_track_positions,
            )
            feature_table[driver_name] = DriverFeatures(
                qualifying_score=qualifying_score,
                recent_form=recent_form,
                track_fit=track_fit,
                pit_efficiency=pit_efficiency,
                reliability=reliability,
            )

        recent_coverage = loaded_recent_races / 3 if loaded_recent_races else 0.0
        track_history_coverage = 1.0 if prior_track_positions else 0.55
        data_completeness = round(
            (1.0 + min(recent_coverage, 1.0) + track_history_coverage) / 3.0,
            2,
        )

        return RetrievedRaceData(
            driver_feature_table=feature_table,
            data_source="FastF1 live qualifying data",
            session_label="Qualifying session",
            data_completeness=data_completeness,
            context_notes=(
                f"Recent form uses {loaded_recent_races} recent completed race(s).",
                "Track fit blends current qualifying pace with prior event history when available.",
            ),
        )

    def get_actual_podium(self, season: str, grand_prix: str) -> tuple[str, str, str] | None:
        fastf1 = self._require_fastf1()
        try:
            event = fastf1.get_event(int(season), grand_prix)
            race_session = fastf1.get_session(int(season), event["EventName"], "R")
            race_session.load(laps=False, telemetry=False, weather=False, messages=False)
            results = race_session.results.head(3)
        except Exception:
            return None

        if results.empty or len(results.index) < 3:
            return None

        podium: list[str] = []
        for _, row in results.iterrows():
            podium.append(self._driver_name(row))

        if len(podium) < 3:
            return None
        return (podium[0], podium[1], podium[2])

    def _load_schedule(self, season: int):
        fastf1 = self._require_fastf1()
        return fastf1.get_event_schedule(season, include_testing=False)

    def _support_mode_for_event(self, event) -> str:
        event_date = event["EventDate"]
        today = datetime.now(timezone.utc).date()
        if hasattr(event_date, "date") and event_date.date() < today:
            return "Race completed"
        return "Live qualifying expected"

    def _load_recent_race_context(
        self,
        season: int,
        current_round: int,
        limit: int = 3,
    ) -> tuple[dict[str, list[dict[str, float | bool]]], int]:
        schedule = self._load_schedule(season)
        prior_events = schedule[schedule["RoundNumber"] < current_round].tail(limit)
        summaries: dict[str, list[dict[str, float | bool]]] = defaultdict(list)
        loaded = 0

        fastf1 = self._require_fastf1()
        for _, event in prior_events.iterrows():
            try:
                race_session = fastf1.get_session(season, event["EventName"], "R")
                race_session.load(
                    laps=False,
                    telemetry=False,
                    weather=False,
                    messages=False,
                )
                results = race_session.results
            except Exception as exc:
                logger.info(
                    "Skipping recent race context for %s %s: %s",
                    season,
                    event["EventName"],
                    exc,
                )
                continue

            if results.empty:
                continue
            loaded += 1
            for _, row in results.iterrows():
                driver_name = self._driver_name(row)
                summaries[driver_name].append(
                    {
                        "finish_position": self._safe_position(
                            row.get("Position") or row.get("ClassifiedPosition")
                        ),
                        "grid_position": self._safe_position(row.get("GridPosition")),
                        "points": float(row.get("Points") or 0.0),
                        "finished": self._did_finish(row),
                    }
                )
        return dict(summaries), loaded

    def _load_previous_track_history(
        self,
        season: int,
        grand_prix: str,
    ) -> dict[str, float]:
        if season <= 2025:
            return {}

        fastf1 = self._require_fastf1()
        try:
            event = fastf1.get_event(season - 1, grand_prix)
            session = fastf1.get_session(season - 1, event["EventName"], "Q")
            session.load(laps=False, telemetry=False, weather=False, messages=False)
            results = session.results
        except Exception:
            return {}

        positions: dict[str, float] = {}
        for _, row in results.iterrows():
            positions[self._driver_name(row)] = self._safe_position(row.get("Position"))
        return positions

    def _collect_best_qualifying_times(self, results) -> dict[str, float]:
        best_times: dict[str, float] = {}
        for _, row in results.iterrows():
            best_seconds = self._best_qualifying_time_seconds(row)
            if best_seconds is None:
                continue
            best_times[self._driver_name(row)] = best_seconds
        return best_times

    def _best_qualifying_time_seconds(self, row) -> float | None:
        for column in ("Q3", "Q2", "Q1", "Time"):
            value = row.get(column)
            if value is None:
                continue
            total_seconds = getattr(value, "total_seconds", None)
            if not callable(total_seconds):
                continue
            seconds = total_seconds()
            if seconds == seconds:
                return float(seconds)
        return None

    def _build_qualifying_score(
        self,
        row,
        best_time_seconds: float | None,
        pole_time_seconds: float,
    ) -> float:
        position = self._safe_position(row.get("Position"))
        if best_time_seconds is None:
            return self._clamp(100.0 - position * 2.8, 45.0, 98.0)
        gap_penalty = max(0.0, best_time_seconds - pole_time_seconds) * 12.0
        return self._clamp(100.0 - position * 2.3 - gap_penalty, 45.0, 99.0)

    def _build_recent_form(
        self,
        qualifying_score: float,
        history: list[dict[str, float | bool]],
    ) -> float:
        if not history:
            return self._clamp(qualifying_score - 3.0, 50.0, 95.0)
        avg_finish = mean(float(entry["finish_position"]) for entry in history)
        avg_points = mean(float(entry["points"]) for entry in history)
        return self._clamp(100.0 - avg_finish * 2.8 + avg_points * 0.8, 48.0, 96.0)

    def _build_reliability(
        self,
        qualifying_score: float,
        history: list[dict[str, float | bool]],
    ) -> float:
        if not history:
            return self._clamp(qualifying_score - 6.0, 48.0, 92.0)
        finish_rate = mean(1.0 if entry["finished"] else 0.0 for entry in history)
        avg_points = mean(float(entry["points"]) for entry in history)
        return self._clamp(58.0 + finish_rate * 32.0 + avg_points * 0.5, 45.0, 98.0)

    def _build_pit_efficiency(
        self,
        qualifying_score: float,
        history: list[dict[str, float | bool]],
    ) -> float:
        if not history:
            return self._clamp(qualifying_score - 8.0, 55.0, 90.0)
        avg_gain = mean(
            float(entry["grid_position"]) - float(entry["finish_position"])
            for entry in history
        )
        finish_rate = mean(1.0 if entry["finished"] else 0.0 for entry in history)
        return self._clamp(78.0 + avg_gain * 3.8 + finish_rate * 6.0, 55.0, 95.0)

    def _build_track_fit(
        self,
        driver_name: str,
        qualifying_score: float,
        recent_form: float,
        prior_track_positions: dict[str, float],
    ) -> float:
        historical_position = prior_track_positions.get(driver_name)
        if historical_position is None:
            return self._clamp(qualifying_score * 0.65 + recent_form * 0.35, 50.0, 97.0)
        history_score = self._clamp(100.0 - historical_position * 2.8, 48.0, 95.0)
        return self._clamp(qualifying_score * 0.55 + history_score * 0.45, 50.0, 97.0)

    def _did_finish(self, row) -> bool:
        status = str(row.get("Status") or "")
        classified_position = str(row.get("ClassifiedPosition") or "")
        if "Finished" in status or status.startswith("+"):
            return True
        return classified_position.isdigit()

    def _driver_name(self, row) -> str:
        return str(
            row.get("FullName")
            or row.get("BroadcastName")
            or row.get("Abbreviation")
            or "Unknown Driver"
        )

    def _safe_position(self, raw_value) -> float:
        try:
            value = float(raw_value)
            if value == value:
                return value
        except (TypeError, ValueError):
            pass
        return 20.0

    def _clamp(self, value: float, lower: float, upper: float) -> float:
        return round(max(lower, min(upper, value)), 1)


class ResilientRaceDataRepository(RaceDataRepository):
    """Legacy test wrapper retained for fixture-based development checks."""

    def __init__(
        self,
        primary: RaceDataRepository,
        fallback: RaceDataRepository,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def get_available_seasons(self) -> list[str]:
        return self.fallback.get_available_seasons()

    def get_available_grand_prix(self, season: str) -> list[str]:
        return self.fallback.get_available_grand_prix(season)

    def get_supported_weekends(self) -> list[RaceWeekendOption]:
        if hasattr(self.fallback, "get_supported_weekends"):
            return self.fallback.get_supported_weekends()

        weekends: list[RaceWeekendOption] = []
        for season in self.get_available_seasons():
            for grand_prix in self.get_available_grand_prix(season):
                weekends.append(
                    RaceWeekendOption(
                        season=season,
                        grand_prix=grand_prix,
                        support_mode="Fixture data (tests only)",
                    )
                )
        return weekends

    def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
        try:
            return self.primary.get_race_features(season, grand_prix)
        except Exception as primary_exc:
            try:
                return self.fallback.get_race_features(season, grand_prix)
            except Exception as fixture_exc:
                fixture_options = []
                try:
                    fixture_options = self.fallback.get_available_grand_prix(season)
                except Exception:
                    fixture_options = []

                guidance = ""
                if fixture_options:
                    guidance = (
                        " Available fixture races for this season: "
                        + ", ".join(fixture_options)
                        + "."
                    )

                raise RuntimeError(
                    "Live data could not be loaded and no fixture data exists "
                    f"for {season} {grand_prix}. "
                    f"Live error: {primary_exc}. "
                    f"Fixture error: {fixture_exc}."
                    + guidance
                ) from fixture_exc
