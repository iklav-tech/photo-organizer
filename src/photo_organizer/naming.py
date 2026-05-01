"""Naming rules for generated photo filenames."""

from __future__ import annotations

from datetime import datetime
import string
from pathlib import Path


_ALLOWED_FILENAME_FIELDS = {"date", "stem", "ext", "original"}


def _validate_pattern_fields(pattern: str, allowed_fields: set[str]) -> None:
    formatter = string.Formatter()
    for _, field_name, _, _ in formatter.parse(pattern):
        if field_name is None:
            continue
        root_name = field_name.split(".", maxsplit=1)[0].split("[", maxsplit=1)[0]
        if root_name not in allowed_fields:
            allowed = ", ".join(sorted(allowed_fields))
            raise ValueError(f"Unknown pattern field '{root_name}'. Allowed: {allowed}")


def validate_filename_pattern(pattern: str) -> None:
    """Validate fields accepted by filename patterns."""
    _validate_pattern_fields(pattern, _ALLOWED_FILENAME_FIELDS)


def build_default_filename(dt: datetime, original_path: str | Path) -> str:
    """Build the default deterministic filename for a photo.

    Format: YYYY-MM-DD_HH-MM-SS.ext
    """
    extension = Path(original_path).suffix
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    return f"{timestamp}{extension}"


def build_pattern_filename(
    dt: datetime,
    original_path: str | Path,
    pattern: str,
) -> str:
    """Build a filename from a user-supplied format pattern."""
    validate_filename_pattern(pattern)
    path = Path(original_path)
    filename = pattern.format(
        date=dt,
        stem=path.stem,
        ext=path.suffix,
        original=path.name,
    )
    if not filename or filename in {".", ".."}:
        raise ValueError("Generated filename is empty or invalid")
    if Path(filename).name != filename:
        raise ValueError("Filename pattern must not contain path separators")
    return filename
