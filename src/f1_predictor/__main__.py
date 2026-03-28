"""Application entry point."""

import logging

from f1_predictor.data.repository import FastF1RaceDataRepository
from f1_predictor.presentation.tk_app import launch_app
from f1_predictor.runtime import configure_fastf1_cache, configure_logging


def main() -> None:
    log_path = configure_logging()
    repository = FastF1RaceDataRepository()
    fastf1_module = getattr(repository, "_fastf1", None)
    if fastf1_module is not None:
        cache_dir = configure_fastf1_cache(fastf1_module)
        logging.getLogger(__name__).info(
            "Runtime ready. Log file: %s%s",
            log_path,
            f" | FastF1 cache: {cache_dir}" if cache_dir else "",
        )
    launch_app(repository)


if __name__ == "__main__":
    main()
