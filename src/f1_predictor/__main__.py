"""Application entry point."""

from f1_predictor.data.repository import (
    FastF1RaceDataRepository,
    LocalJsonRaceDataRepository,
    ResilientRaceDataRepository,
)
from f1_predictor.presentation.tk_app import launch_app


def main() -> None:
    repository = ResilientRaceDataRepository(
        primary=FastF1RaceDataRepository(),
        fallback=LocalJsonRaceDataRepository(),
    )
    launch_app(repository)


if __name__ == "__main__":
    main()

