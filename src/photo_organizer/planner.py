"""Path planning helpers for destination directories."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path, PurePath

from photo_organizer.metadata import get_best_available_datetime


def build_date_destination(base_dir: str | PurePath, dt: datetime) -> PurePath:
    """Build destination directory using YYYY/MM/DD structure."""
    base_path: PurePath = Path(base_dir) if isinstance(base_dir, str) else base_dir
    return base_path / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")


def build_date_destination_for_file(
    base_dir: str | PurePath, file_path: str | Path
) -> PurePath:
    """Build destination directory from the best resolved date for a file."""
    resolved_dt = get_best_available_datetime(file_path)
    return build_date_destination(base_dir, resolved_dt)
