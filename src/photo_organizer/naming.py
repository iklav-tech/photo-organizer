"""Naming rules for generated photo filenames."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def build_default_filename(dt: datetime, original_path: str | Path) -> str:
    """Build the default deterministic filename for a photo.

    Format: YYYY-MM-DD_HH-MM-SS.ext
    """
    extension = Path(original_path).suffix
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    return f"{timestamp}{extension}"
