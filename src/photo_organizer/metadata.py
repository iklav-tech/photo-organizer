"""Metadata helpers for photo dates."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


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
    """Read EXIF datetime-like fields from a file."""
    fields = extract_exif_metadata(path)

    # Common alias used in tools: "CreateDate" usually maps to DateTime (306).
    if "CreateDate" not in fields:
        for alias in ("DateTime", "DateTimeDigitized"):
            if alias in fields:
                fields["CreateDate"] = fields[alias]
                break

    return fields


def extract_exif_metadata(path: str | Path) -> dict[str, Any]:
    """Extract EXIF tags from a supported image file.

    Returns an empty dict when EXIF data is unavailable, the image has no EXIF,
    or a safe read error happens.
    """
    file_path = Path(path)

    try:
        from PIL import ExifTags, Image
    except ImportError:
        logger.debug("Pillow not available; EXIF extraction skipped for file=%s", file_path)
        return {}

    try:
        with Image.open(file_path) as image:
            exif_data = image.getexif()
    except Exception as exc:
        logger.warning("Failed to read EXIF for file=%s error=%s", file_path, exc)
        return {}

    if not exif_data:
        return {}

    fields: dict[str, Any] = {}
    for key, value in exif_data.items():
        tag_name = ExifTags.TAGS.get(key)
        if isinstance(tag_name, str):
            fields[tag_name] = value

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
            logger.info("Datetime resolved from %s for file=%s", field_name, file_path)
            return parsed

    logger.info("Datetime fallback to file modification time for file=%s", file_path)
    return datetime.fromtimestamp(file_path.stat().st_mtime)
