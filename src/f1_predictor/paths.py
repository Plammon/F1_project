"""Helpers for locating bundled resources in dev and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", project_root()))
    return project_root()


def resolve_path(*parts: str) -> Path:
    """Resolve a resource path for both editable and frozen app builds."""
    candidates = [
        project_root().joinpath(*parts),
        bundled_root().joinpath(*parts),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]

