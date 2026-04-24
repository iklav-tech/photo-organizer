"""Metadata helpers for photo dates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_exif_datetime(value: Any) -> datetime | None:
    """Parse common EXIF datetime string formats into a datetime."""
    if value is None:
        return None

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    formats = (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    )
    for candidate_format in formats:
        try:
            return datetime.strptime(text, candidate_format)
        except ValueError:
            continue

    return None


def _read_exif_datetime_fields(path: Path) -> dict[str, Any]:
    """Read EXIF datetime-like fields from a file.

    Returns an empty dict when EXIF data is unavailable or Pillow is not installed.
    """
    try:
        from PIL import ExifTags, Image
    except ImportError:
        return {}

    try:
        with Image.open(path) as image:
            exif_data = image.getexif()
    except Exception:
        return {}

    if not exif_data:
        return {}

    fields: dict[str, Any] = {}
    for key, value in exif_data.items():
        tag_name = ExifTags.TAGS.get(key)
        if isinstance(tag_name, str):
            fields[tag_name] = value

    # Common alias used in tools: "CreateDate" usually maps to DateTime (306).
    if "CreateDate" not in fields:
        for alias in ("DateTime", "DateTimeDigitized"):
            if alias in fields:
                fields["CreateDate"] = fields[alias]
                break

    return fields


def get_best_available_datetime(path: str | Path) -> datetime:
    """Return the best available datetime for a file.

    Priority order:
    1. EXIF DateTimeOriginal
    2. EXIF CreateDate
    3. File modification time (mtime)
    """
    file_path = Path(path)
    exif_fields = _read_exif_datetime_fields(file_path)

    for field_name in ("DateTimeOriginal", "CreateDate"):
        parsed = _parse_exif_datetime(exif_fields.get(field_name))
        if parsed is not None:
            return parsed

    return datetime.fromtimestamp(file_path.stat().st_mtime)
