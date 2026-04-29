"""Path planning helpers for destination directories."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path, PurePath
import re
from typing import Protocol

from photo_organizer.metadata import get_best_available_datetime


class LocationLike(Protocol):
    country: str | None
    state: str | None
    city: str | None


def _clean_location_part(value: str | None) -> str:
    if value is None:
        return "Unknown"

    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value.strip())
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "Unknown"


def build_date_destination(base_dir: str | PurePath, dt: datetime) -> PurePath:
    """Build destination directory using YYYY/MM/DD structure."""
    base_path: PurePath = Path(base_dir) if isinstance(base_dir, str) else base_dir
    return base_path / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")


def build_location_destination(
    base_dir: str | PurePath,
    location: LocationLike,
) -> PurePath:
    """Build destination directory using country/state/city structure."""
    base_path: PurePath = Path(base_dir) if isinstance(base_dir, str) else base_dir
    return (
        base_path
        / _clean_location_part(location.country)
        / _clean_location_part(location.state)
        / _clean_location_part(location.city)
    )


def build_date_destination_for_file(
    base_dir: str | PurePath, file_path: str | Path
) -> PurePath:
    """Build destination directory from the best resolved date for a file."""
    resolved_dt = get_best_available_datetime(file_path)
    return build_date_destination(base_dir, resolved_dt)
