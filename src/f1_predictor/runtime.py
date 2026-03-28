"""Runtime bootstrap helpers for desktop launches."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from f1_predictor.paths import project_root


def configure_logging() -> Path:
    logs_dir = project_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "f1_predictor.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_path
        for handler in root_logger.handlers
    ):
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)

    return log_path


def configure_fastf1_cache(fastf1_module) -> Path | None:
    cache_dir = project_root() / "cache" / "fastf1"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_api = getattr(fastf1_module, "Cache", None)
    if cache_api is None or not hasattr(cache_api, "enable_cache"):
        return None
    cache_api.enable_cache(str(cache_dir))
    return cache_dir
