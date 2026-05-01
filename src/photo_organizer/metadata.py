"""Metadata helpers for photo dates.

Metadata conflict policy
------------------------

The organizer resolves metadata conflicts through the explicit
``METADATA_PRECEDENCE_POLICY`` matrix below. Each candidate declares the logical
field it can populate, the metadata source, the source role and whether the
current reader already implements it.

Roles:
- ``primary``: preferred authoritative embedded metadata for that field.
- ``fallback``: accepted embedded metadata when primary data is unavailable.
- ``heuristic``: derived or filesystem data used only when embedded metadata is
  absent or unusable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Literal

from photo_organizer.constants import EXIF_IMAGE_FILE_EXTENSIONS


logger = logging.getLogger(__name__)


MetadataFieldName = Literal["date_taken", "location", "title", "author", "description"]
MetadataSourceRole = Literal["primary", "fallback", "heuristic"]
MetadataSupportStatus = Literal["implemented", "planned"]


@dataclass(frozen=True)
class MetadataPrecedenceRule:
    """One ordered metadata candidate for resolving a logical field."""

    field: MetadataFieldName
    role: MetadataSourceRole
    source: str
    keys: tuple[str, ...]
    support: MetadataSupportStatus
    notes: str = ""


METADATA_PRECEDENCE_POLICY: tuple[MetadataPrecedenceRule, ...] = (
    MetadataPrecedenceRule(
        field="date_taken",
        role="primary",
        source="EXIF",
        keys=("DateTimeOriginal",),
        support="implemented",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="fallback",
        source="EXIF",
        keys=("CreateDate", "DateTime", "DateTimeDigitized"),
        support="implemented",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="fallback",
        source="XMP",
        keys=("exif:DateTimeOriginal", "xmp:CreateDate"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="fallback",
        source="IPTC-IIM",
        keys=("DateCreated", "TimeCreated"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="fallback",
        source="PNG metadata",
        keys=("Creation Time", "CreationTime"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="heuristic",
        source="Filesystem",
        keys=("mtime",),
        support="implemented",
        notes="Used only when embedded date metadata is missing or invalid.",
    ),
    MetadataPrecedenceRule(
        field="location",
        role="primary",
        source="EXIF",
        keys=("GPSInfo", "GPSLatitude", "GPSLongitude"),
        support="implemented",
    ),
    MetadataPrecedenceRule(
        field="location",
        role="fallback",
        source="XMP",
        keys=("exif:GPSLatitude", "exif:GPSLongitude"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="location",
        role="fallback",
        source="IPTC-IIM",
        keys=("City", "Province-State", "Country-PrimaryLocationName"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="location",
        role="heuristic",
        source="Reverse geocoding",
        keys=("GPSLatitudeDecimal", "GPSLongitudeDecimal"),
        support="implemented",
        notes="Derives city/state/country from resolved GPS coordinates.",
    ),
    MetadataPrecedenceRule(
        field="title",
        role="primary",
        source="XMP",
        keys=("dc:title", "photoshop:Headline"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="title",
        role="fallback",
        source="IPTC-IIM",
        keys=("ObjectName", "Headline"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="title",
        role="fallback",
        source="PNG metadata",
        keys=("Title",),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="title",
        role="fallback",
        source="EXIF",
        keys=("ImageDescription",),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="author",
        role="primary",
        source="XMP",
        keys=("dc:creator",),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="author",
        role="fallback",
        source="IPTC-IIM",
        keys=("By-line", "Writer-Editor"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="author",
        role="fallback",
        source="PNG metadata",
        keys=("Author",),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="author",
        role="fallback",
        source="EXIF",
        keys=("Artist", "Copyright"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="description",
        role="primary",
        source="XMP",
        keys=("dc:description",),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="description",
        role="fallback",
        source="IPTC-IIM",
        keys=("Caption-Abstract",),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="description",
        role="fallback",
        source="PNG metadata",
        keys=("Description", "Comment"),
        support="planned",
    ),
    MetadataPrecedenceRule(
        field="description",
        role="fallback",
        source="EXIF",
        keys=("ImageDescription", "UserComment"),
        support="planned",
    ),
)


def get_metadata_precedence_policy(
    field: MetadataFieldName | None = None,
) -> tuple[MetadataPrecedenceRule, ...]:
    """Return the ordered metadata precedence policy.

    When ``field`` is provided, only rules for that logical field are returned,
    preserving priority order.
    """
    if field is None:
        return METADATA_PRECEDENCE_POLICY
    return tuple(rule for rule in METADATA_PRECEDENCE_POLICY if rule.field == field)


@dataclass(frozen=True)
class DateTimeResolution:
    """Resolved datetime and whether it came from the mtime fallback."""

    value: datetime
    used_fallback: bool


@dataclass(frozen=True)
class GPSCoordinates:
    """Resolved GPS coordinates in decimal degrees."""

    latitude: float
    longitude: float


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


def _rational_to_float(value: Any) -> float | None:
    """Convert common EXIF rational values to float."""
    try:
        if isinstance(value, tuple) and len(value) == 2:
            numerator, denominator = value
            if denominator == 0:
                return None
            return float(numerator) / float(denominator)
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _gps_dms_to_decimal(value: Any, ref: Any) -> float | None:
    """Convert EXIF GPS degrees/minutes/seconds to signed decimal degrees."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None

    degrees = _rational_to_float(value[0])
    minutes = _rational_to_float(value[1])
    seconds = _rational_to_float(value[2])
    if degrees is None or minutes is None or seconds is None:
        return None

    decimal = degrees + minutes / 60 + seconds / 3600

    if isinstance(ref, bytes):
        ref = ref.decode("ascii", errors="ignore")
    if isinstance(ref, str) and ref.strip().upper() in {"S", "W"}:
        decimal *= -1

    return decimal


def _normalize_gps_info(gps_info: Any, gps_tags: dict[int, str]) -> dict[str, Any]:
    """Convert Pillow's numeric GPS tag ids to EXIF GPS tag names."""
    if not hasattr(gps_info, "items"):
        return {}

    normalized: dict[str, Any] = {}
    try:
        gps_items = gps_info.items()
    except Exception as exc:
        logger.warning("Failed to parse GPS EXIF block: error=%s", exc)
        return {}

    for key, value in gps_items:
        tag_name = gps_tags.get(key)
        if isinstance(tag_name, str):
            normalized[tag_name] = value

    return normalized


def _read_gps_ifd(exif_data: Any, gps_key: int) -> Any:
    if not hasattr(exif_data, "get_ifd"):
        return None

    try:
        return exif_data.get_ifd(gps_key)
    except Exception as exc:
        logger.warning("Failed to read GPS EXIF IFD: error=%s", exc)
        return None


def _extract_gps_coordinates_from_fields(fields: dict[str, Any]) -> GPSCoordinates | None:
    """Read decimal GPS coordinates from normalized EXIF fields."""
    gps_info = fields.get("GPSInfo")
    if not isinstance(gps_info, dict):
        return None

    latitude = _gps_dms_to_decimal(
        gps_info.get("GPSLatitude"),
        gps_info.get("GPSLatitudeRef"),
    )
    longitude = _gps_dms_to_decimal(
        gps_info.get("GPSLongitude"),
        gps_info.get("GPSLongitudeRef"),
    )
    if latitude is None or longitude is None:
        return None

    return GPSCoordinates(latitude=latitude, longitude=longitude)


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
    if file_path.suffix.lower() not in EXIF_IMAGE_FILE_EXTENSIONS:
        logger.debug(
            "EXIF extraction skipped for unsupported metadata format: file=%s",
            file_path,
        )
        return {}

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

    try:
        exif_items = exif_data.items()
    except Exception as exc:
        logger.warning("Failed to parse EXIF for file=%s error=%s", file_path, exc)
        return {}

    fields: dict[str, Any] = {}
    gps_tags = getattr(ExifTags, "GPSTAGS", {})
    for key, value in exif_items:
        tag_name = ExifTags.TAGS.get(key)
        if isinstance(tag_name, str):
            if tag_name == "GPSInfo":
                value = _normalize_gps_info(value, gps_tags)
                if not value:
                    value = _normalize_gps_info(_read_gps_ifd(exif_data, key), gps_tags)
            fields[tag_name] = value

    gps_coordinates = _extract_gps_coordinates_from_fields(fields)
    if gps_coordinates is not None:
        fields["GPSLatitudeDecimal"] = gps_coordinates.latitude
        fields["GPSLongitudeDecimal"] = gps_coordinates.longitude

    return fields


def extract_gps_coordinates(path: str | Path) -> GPSCoordinates | None:
    """Extract GPS coordinates in decimal degrees when available."""
    return _extract_gps_coordinates_from_fields(extract_exif_metadata(path))


def resolve_best_available_datetime(path: str | Path) -> DateTimeResolution:
    """Return the best available datetime plus fallback metadata.

    Implements the currently supported `date_taken` subset of
    `METADATA_PRECEDENCE_POLICY`:
    1. EXIF DateTimeOriginal (primary)
    2. EXIF CreateDate/DateTime/DateTimeDigitized (fallback)
    3. Filesystem modification time (heuristic)
    """
    file_path = Path(path)
    exif_fields = _read_exif_datetime_fields(file_path)

    for field_name in ("DateTimeOriginal", "CreateDate"):
        parsed = _parse_exif_datetime(exif_fields.get(field_name))
        if parsed is not None:
            logger.info("Datetime resolved from %s for file=%s", field_name, file_path)
            return DateTimeResolution(value=parsed, used_fallback=False)

    logger.info("Datetime fallback to file modification time for file=%s", file_path)
    return DateTimeResolution(
        value=datetime.fromtimestamp(file_path.stat().st_mtime),
        used_fallback=True,
    )


def get_best_available_datetime(path: str | Path) -> datetime:
    """Return the best available datetime for a file."""
    return resolve_best_available_datetime(path).value
