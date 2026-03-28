from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor.data.repository import (
    LocalJsonRaceDataRepository,
    RaceDataRepository,
    ResilientRaceDataRepository,
)
from f1_predictor.domain.models import RetrievedRaceData


class RepositoryTests(unittest.TestCase):
    def test_local_repository_lists_seasons_and_events(self) -> None:
        repository = LocalJsonRaceDataRepository()
        self.assertEqual(repository.get_available_seasons(), ["2025", "2026"])
        self.assertIn(
            "Australian Grand Prix",
            repository.get_available_grand_prix("2025"),
        )
        weekends = repository.get_supported_weekends()
        self.assertGreaterEqual(len(weekends), 6)
        self.assertEqual(weekends[0].support_mode, "Fixture data (tests only)")

    def test_resilient_repository_falls_back_when_primary_fails(self) -> None:
        class BrokenRepository(RaceDataRepository):
            def get_available_seasons(self) -> list[str]:
                raise RuntimeError("primary unavailable")

            def get_available_grand_prix(self, season: str) -> list[str]:
                raise RuntimeError("primary unavailable")

            def get_supported_weekends(self):
                raise RuntimeError("primary unavailable")

            def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
                raise RuntimeError("primary unavailable")

        repository = ResilientRaceDataRepository(
            primary=BrokenRepository(),
            fallback=LocalJsonRaceDataRepository(),
        )
        result = repository.get_race_features("2025", "Australian Grand Prix")
        self.assertEqual(result.data_source, "Fixture dataset")
        self.assertIn("Monaco Grand Prix", repository.get_available_grand_prix("2026"))

    def test_resilient_repository_raises_clear_message_when_both_sources_fail(self) -> None:
        class BrokenRepository(RaceDataRepository):
            def get_available_seasons(self) -> list[str]:
                raise RuntimeError("primary unavailable")

            def get_available_grand_prix(self, season: str) -> list[str]:
                raise RuntimeError("primary unavailable")

            def get_supported_weekends(self):
                raise RuntimeError("primary unavailable")

            def get_race_features(self, season: str, grand_prix: str) -> RetrievedRaceData:
                raise RuntimeError("live source unavailable")

        repository = ResilientRaceDataRepository(
            primary=BrokenRepository(),
            fallback=LocalJsonRaceDataRepository(),
        )

        with self.assertRaises(RuntimeError) as context:
            repository.get_race_features("2025", "Abu Dhabi Grand Prix")

        self.assertIn("no fixture data exists", str(context.exception))
        self.assertIn("Australian Grand Prix", str(context.exception))


if __name__ == "__main__":
    unittest.main()
