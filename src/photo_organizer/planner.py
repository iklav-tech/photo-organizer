"""Path planning helpers for destination directories."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path, PurePath
import re
import string
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


def _clean_destination_part(value: str) -> str:
    text = re.sub(r'[<>:"\\|?*\x00-\x1f]', "-", value.strip())
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "Unknown"


def _validate_pattern_fields(pattern: str, allowed_fields: set[str]) -> None:
    formatter = string.Formatter()
    for _, field_name, _, _ in formatter.parse(pattern):
        if field_name is None:
            continue
        root_name = field_name.split(".", maxsplit=1)[0].split("[", maxsplit=1)[0]
        if root_name not in allowed_fields:
            allowed = ", ".join(sorted(allowed_fields))
            raise ValueError(f"Unknown pattern field '{root_name}'. Allowed: {allowed}")


def validate_destination_pattern(pattern: str) -> None:
    """Validate fields accepted by destination patterns."""
    _validate_pattern_fields(pattern, {"date", "country", "state", "city"})


def build_date_destination(base_dir: str | PurePath, dt: datetime) -> PurePath:
    """Build destination directory using YYYY/MM/DD structure."""
    base_path: PurePath = Path(base_dir) if isinstance(base_dir, str) else base_dir
    return base_path / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")


def build_pattern_destination(
    base_dir: str | PurePath,
    dt: datetime,
    pattern: str,
    location: LocationLike | None = None,
) -> PurePath:
    """Build destination directory from a user-supplied format pattern."""
    validate_destination_pattern(pattern)
    country = _clean_location_part(location.country if location is not None else None)
    state = _clean_location_part(location.state if location is not None else None)
    city = _clean_location_part(location.city if location is not None else None)
    formatted = pattern.format(
        date=dt,
        country=country,
        state=state,
        city=city,
    )
    parts = [
        _clean_destination_part(part)
        for part in re.split(r"[\\/]+", formatted)
        if part.strip()
    ]
    if not parts:
        raise ValueError("Generated destination path is empty")

    base_path: PurePath = Path(base_dir) if isinstance(base_dir, str) else base_dir
    destination = base_path
    for part in parts:
        destination = destination / part
    return destination


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


def build_location_date_destination(
    base_dir: str | PurePath,
    location: LocationLike,
    dt: datetime,
) -> PurePath:
    """Build destination directory using country/state/city/YYYY/MM structure."""
    return (
        build_location_destination(base_dir, location)
        / dt.strftime("%Y")
        / dt.strftime("%m")
    )


def build_city_state_month_destination(
    base_dir: str | PurePath,
    location: LocationLike,
    dt: datetime,
) -> PurePath:
    """Build destination directory using City-State/YYYY-MM structure."""
    base_path: PurePath = Path(base_dir) if isinstance(base_dir, str) else base_dir
    city_state = (
        f"{_clean_location_part(location.city)}-"
        f"{_clean_location_part(location.state)}"
    )
    return base_path / city_state / dt.strftime("%Y-%m")


def build_date_destination_for_file(
    base_dir: str | PurePath, file_path: str | Path
) -> PurePath:
    """Build destination directory from the best resolved date for a file."""
    resolved_dt = get_best_available_datetime(file_path)
    return build_date_destination(base_dir, resolved_dt)
