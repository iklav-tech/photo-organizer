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

from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any, Callable, Literal
import xml.etree.ElementTree as ET
import zlib

from photo_organizer.constants import (
    EXIF_IMAGE_FILE_EXTENSIONS,
    HEIF_IMAGE_FILE_EXTENSIONS,
    IMAGE_FILE_EXTENSIONS,
    RAW_IMAGE_FILE_EXTENSIONS,
)
from photo_organizer.correction_manifest import CorrectionApplication
from photo_organizer.heif_backend import (
    HeifBackendError,
    HeifContainerInfo,
    HeifDependencyError,
    HeifImageInfo,
    PillowHeifBackend,
)
from photo_organizer.raw_backend import RawMetadataError, TiffRawMetadataBackend
from photo_organizer.text_normalization import normalize_text


logger = logging.getLogger(__name__)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_TEXT_CHUNK_TYPES = {"iTXt", "tEXt", "zTXt"}
FALLBACK_EXIF_TAGS = {
    270: "ImageDescription",
    306: "DateTime",
    315: "Artist",
    33432: "Copyright",
    34853: "GPSInfo",
    36867: "DateTimeOriginal",
    36868: "DateTimeDigitized",
}


MetadataFieldName = Literal["date_taken", "location", "title", "author", "description"]
MetadataSourceRole = Literal["primary", "fallback", "heuristic"]
MetadataSupportStatus = Literal["implemented", "planned"]
MetadataConfidence = Literal["high", "medium", "low"]
DateValueKind = Literal["captured", "inferred"]
ReconciliationPolicy = Literal["precedence", "newest", "oldest", "filesystem"]
RECONCILIATION_POLICY_CHOICES = ("precedence", "newest", "oldest", "filesystem")
DATE_HEURISTICS_DEFAULT = True


@dataclass(frozen=True)
class MetadataPrecedenceRule:
    """One ordered metadata candidate for resolving a logical field."""

    field: MetadataFieldName
    role: MetadataSourceRole
    source: str
    keys: tuple[str, ...]
    support: MetadataSupportStatus
    notes: str = ""


@dataclass(frozen=True)
class MetadataProvenance:
    """Origin details for a resolved metadata value."""

    source: str
    field: str
    confidence: MetadataConfidence
    raw_value: Any

    @property
    def label(self) -> str:
        """Return a concise source label such as EXIF:DateTimeOriginal."""
        return f"{self.source}:{self.field}"


@dataclass(frozen=True)
class MetadataCandidate:
    """One parsed candidate value from a metadata source."""

    value: Any
    provenance: MetadataProvenance
    role: MetadataSourceRole
    precedence: int
    used_fallback: bool = False
    date_kind: DateValueKind = "captured"


@dataclass(frozen=True)
class ReconciliationDecision:
    """The selected candidate and the reason it won."""

    field: MetadataFieldName
    policy: ReconciliationPolicy
    selected: MetadataCandidate
    candidates: tuple[MetadataCandidate, ...]
    reason: str
    conflict: bool = False

    @property
    def conflicting_sources(self) -> tuple[str, ...]:
        if not self.conflict:
            return ()
        return tuple(candidate.provenance.label for candidate in self.candidates)


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
        support="implemented",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="fallback",
        source="IPTC-IIM",
        keys=("DateCreated", "TimeCreated"),
        support="implemented",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="fallback",
        source="PNG metadata",
        keys=("Creation Time", "CreationTime", "tIME"),
        support="implemented",
        notes=(
            "tIME is an image modification timestamp and is used only as "
            "secondary fallback."
        ),
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="heuristic",
        source="Sidecar external",
        keys=("date_taken", "datetime", "created_at", "DateTimeOriginal", "CreateDate"),
        support="implemented",
        notes="Used as low-confidence inferred date from same-basename sidecars.",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="heuristic",
        source="Filename",
        keys=("date pattern",),
        support="implemented",
        notes="Used as low-confidence inferred date from safe filename patterns.",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="heuristic",
        source="Folder",
        keys=("date pattern",),
        support="implemented",
        notes="Used as low-confidence inferred date from parent folder names.",
    ),
    MetadataPrecedenceRule(
        field="date_taken",
        role="heuristic",
        source="Sequence batch",
        keys=("sibling date pattern",),
        support="implemented",
        notes="Used as low-confidence inferred date from sibling batch context.",
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
        support="implemented",
    ),
    MetadataPrecedenceRule(
        field="location",
        role="fallback",
        source="IPTC-IIM",
        keys=("City", "Province-State", "Country-PrimaryLocationName"),
        support="implemented",
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
        support="implemented",
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
        support="implemented",
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
        support="implemented",
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
    provenance: MetadataProvenance | None = None
    reconciliation: ReconciliationDecision | None = None
    date_kind: DateValueKind = "captured"


@dataclass(frozen=True)
class GPSCoordinates:
    """Resolved GPS coordinates in decimal degrees."""

    latitude: float
    longitude: float
    provenance: MetadataProvenance | None = dataclass_field(
        default=None,
        compare=False,
    )


@dataclass(frozen=True)
class NormalizedMetadataValue:
    """One logical metadata value with original-field provenance."""

    field: str
    value: Any
    provenance: MetadataProvenance


@dataclass(frozen=True)
class NormalizedImageMetadata:
    """Schema consumed by organization logic regardless of source tag names."""

    date_taken_candidates: tuple[MetadataCandidate, ...] = ()
    camera_make: NormalizedMetadataValue | None = None
    camera_model: NormalizedMetadataValue | None = None
    gps_coordinates: GPSCoordinates | None = None


XMP_NAMESPACE_PREFIXES = {
    "http://ns.adobe.com/xap/1.0/": "xmp",
    "http://ns.adobe.com/exif/1.0/": "exif",
    "http://ns.adobe.com/tiff/1.0/": "tiff",
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://ns.adobe.com/photoshop/1.0/": "photoshop",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
}

XMP_RELEVANT_FIELDS = {
    "xmp:CreateDate",
    "xmp:ModifyDate",
    "exif:DateTimeOriginal",
    "exif:GPSLatitude",
    "exif:GPSLongitude",
    "exif:GPSLatitudeRef",
    "exif:GPSLongitudeRef",
    "tiff:Make",
    "tiff:Model",
    "dc:title",
    "dc:creator",
    "dc:description",
    "photoshop:DateCreated",
    "photoshop:City",
    "photoshop:State",
    "photoshop:Country",
}


IPTC_IIM_DATASETS = {
    (2, 5): "ObjectName",
    (2, 55): "DateCreated",
    (2, 60): "TimeCreated",
    (2, 80): "By-line",
    (2, 90): "City",
    (2, 95): "Province-State",
    (2, 101): "Country-PrimaryLocationName",
    (2, 105): "Headline",
    (2, 120): "Caption-Abstract",
    (2, 122): "Writer-Editor",
}

EXIF_DATE_FIELD_ALIASES: tuple[tuple[str, MetadataConfidence, str], ...] = (
    ("DateTimeOriginal", "high", "DateTimeOriginal"),
    ("CaptureDate", "high", "DateTimeOriginal"),
    ("DateCreated", "medium", "CreateDate"),
    ("CreateDate", "medium", "CreateDate"),
    ("DateTime", "medium", "CreateDate"),
    ("DateTimeDigitized", "medium", "CreateDate"),
)
EXIF_CAMERA_MAKE_FIELDS = ("Make", "CameraMake", "CameraManufacturer", "Manufacturer")
EXIF_CAMERA_MODEL_FIELDS = ("Model", "CameraModel", "CameraModelName")
XMP_CAMERA_MAKE_FIELDS = ("tiff:Make", "exif:Make")
XMP_CAMERA_MODEL_FIELDS = ("tiff:Model", "exif:Model")


def _parse_exif_datetime(value: Any) -> datetime | None:
    """Parse common EXIF datetime string formats into a datetime."""
    if value is None:
        return None

    if isinstance(value, bytes):
        value = normalize_text(value).value

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    formats = (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    )
    for candidate_format in formats:
        try:
            return datetime.strptime(text, candidate_format)
        except ValueError:
            continue

    try:
        iso_text = text.removesuffix("Z") + ("+00:00" if text.endswith("Z") else "")
        parsed = datetime.fromisoformat(iso_text)
        return parsed.replace(tzinfo=None)
    except ValueError:
        pass

    return None


def _parse_iptc_datetime(date_value: Any, time_value: Any = None) -> datetime | None:
    """Parse IPTC-IIM DateCreated and optional TimeCreated fields."""
    if isinstance(date_value, bytes):
        date_value = normalize_text(date_value).value
    if not isinstance(date_value, str):
        return None

    date_text = date_value.strip()
    if not re.fullmatch(r"\d{8}", date_text):
        return None

    time_text = "000000"
    if isinstance(time_value, bytes):
        time_value = normalize_text(time_value).value
    if isinstance(time_value, str) and time_value.strip():
        match = re.match(r"^(\d{2})(\d{2})(\d{2})", time_value.strip())
        if match:
            time_text = "".join(match.groups())

    try:
        return datetime.strptime(f"{date_text}{time_text}", "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _parse_png_time(value: bytes) -> datetime | None:
    """Parse a PNG tIME chunk as a UTC-style naive datetime."""
    if len(value) != 7:
        return None

    year = int.from_bytes(value[0:2], "big")
    month, day, hour, minute, second = value[2:]
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def _format_png_time(value: datetime) -> str:
    return value.strftime("%Y:%m:%d %H:%M:%S")


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
        ref = normalize_text(ref).value
    if isinstance(ref, str) and ref.strip().upper() in {"S", "W"}:
        decimal *= -1

    return decimal


def _xmp_gps_to_decimal(value: Any, ref: Any = None) -> float | None:
    """Convert common XMP GPS values to signed decimal degrees."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        decimal = float(value)
        text_ref = str(ref or "").strip().upper()
        return -abs(decimal) if text_ref in {"S", "W"} else decimal

    if isinstance(value, bytes):
        value = normalize_text(value).value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    trailing_ref = ""
    if text[-1:].upper() in {"N", "S", "E", "W"}:
        trailing_ref = text[-1:].upper()
        text = text[:-1].strip()
    text_ref = trailing_ref or str(ref or "").strip().upper()

    try:
        decimal = float(text)
    except ValueError:
        parts = [part for part in re.split(r"[,\s]+", text) if part]
        if not parts:
            return None
        numeric_parts: list[float] = []
        for part in parts[:3]:
            try:
                numeric_parts.append(float(part))
            except ValueError:
                return None
        degrees = numeric_parts[0]
        minutes = numeric_parts[1] if len(numeric_parts) > 1 else 0.0
        seconds = numeric_parts[2] if len(numeric_parts) > 2 else 0.0
        decimal = abs(degrees) + minutes / 60 + seconds / 3600

    if text_ref in {"S", "W"}:
        decimal = -abs(decimal)
    return decimal


def _qualified_xmp_name(name: str) -> str:
    if name.startswith("{"):
        namespace, _, local_name = name[1:].partition("}")
        prefix = XMP_NAMESPACE_PREFIXES.get(namespace, namespace)
        return f"{prefix}:{local_name}"
    return name


def _decode_iptc_value(value: bytes) -> str:
    return normalize_text(value).value.strip("\x00").strip()


def _decode_png_latin1(value: bytes) -> str:
    return normalize_text(value).value.strip("\x00").strip()


def _decode_png_utf8(value: bytes) -> str:
    return normalize_text(value).value.strip("\x00").strip()


def _split_png_null_field(data: bytes, offset: int = 0) -> tuple[bytes, int] | None:
    end = data.find(b"\x00", offset)
    if end < 0:
        return None
    return data[offset:end], end + 1


def _iter_png_chunks(data: bytes) -> list[tuple[str, bytes]]:
    if not data.startswith(PNG_SIGNATURE):
        return []

    chunks: list[tuple[str, bytes]] = []
    offset = len(PNG_SIGNATURE)
    while offset + 8 <= len(data):
        chunk_length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type_bytes = data[offset + 4 : offset + 8]
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + chunk_length
        chunk_crc_end = chunk_data_end + 4
        if chunk_crc_end > len(data):
            break

        try:
            chunk_type = chunk_type_bytes.decode("ascii")
        except UnicodeDecodeError:
            break

        chunks.append((chunk_type, data[chunk_data_start:chunk_data_end]))
        offset = chunk_crc_end
        if chunk_type == "IEND":
            break

    return chunks


def _parse_png_text_chunk(chunk_type: str, chunk_data: bytes) -> tuple[str, str] | None:
    keyword_info = _split_png_null_field(chunk_data)
    if keyword_info is None:
        return None

    keyword_raw, value_offset = keyword_info
    keyword = _decode_png_latin1(keyword_raw)
    if not keyword:
        return None

    if chunk_type == "tEXt":
        return keyword, _decode_png_latin1(chunk_data[value_offset:])

    if chunk_type == "zTXt":
        if value_offset >= len(chunk_data):
            return None
        compression_method = chunk_data[value_offset]
        if compression_method != 0:
            return None
        try:
            value = zlib.decompress(chunk_data[value_offset + 1 :])
        except zlib.error:
            return None
        return keyword, _decode_png_latin1(value)

    if chunk_type == "iTXt":
        if value_offset + 2 > len(chunk_data):
            return None
        compression_flag = chunk_data[value_offset]
        compression_method = chunk_data[value_offset + 1]
        value_offset += 2

        language_info = _split_png_null_field(chunk_data, value_offset)
        if language_info is None:
            return None
        _, value_offset = language_info

        translated_keyword_info = _split_png_null_field(chunk_data, value_offset)
        if translated_keyword_info is None:
            return None
        _, value_offset = translated_keyword_info

        value = chunk_data[value_offset:]
        if compression_flag == 1:
            if compression_method != 0:
                return None
            try:
                value = zlib.decompress(value)
            except zlib.error:
                return None
        elif compression_flag != 0:
            return None

        return keyword, _decode_png_utf8(value)

    return None


def extract_png_metadata(path: str | Path) -> dict[str, Any]:
    """Extract PNG textual metadata and tIME modification timestamp.

    PNG text chunks are exposed by keyword. `iTXt` values are decoded as UTF-8,
    while legacy `tEXt` and `zTXt` values follow PNG's Latin-1 text encoding.
    """
    file_path = Path(path)
    if file_path.suffix.lower() != ".png":
        return {}

    try:
        data = file_path.read_bytes()
    except OSError as exc:
        logger.warning("Failed to read PNG metadata for file=%s error=%s", file_path, exc)
        return {}

    fields: dict[str, Any] = {}
    field_sources: dict[str, str] = {}
    for chunk_type, chunk_data in _iter_png_chunks(data):
        if chunk_type in PNG_TEXT_CHUNK_TYPES:
            parsed_text = _parse_png_text_chunk(chunk_type, chunk_data)
            if parsed_text is None:
                continue
            keyword, value = parsed_text
            if value:
                fields[keyword] = value
                field_sources[keyword] = chunk_type
            continue

        if chunk_type == "tIME":
            parsed_time = _parse_png_time(chunk_data)
            if parsed_time is not None:
                fields["tIME"] = _format_png_time(parsed_time)
                field_sources["tIME"] = "tIME"

    if field_sources:
        fields["PNGFieldSources"] = field_sources
    return fields


def _read_iptc_dataset_length(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset + 2 > len(data):
        return None

    raw_length = int.from_bytes(data[offset : offset + 2], "big")
    offset += 2
    if raw_length & 0x8000:
        length_byte_count = raw_length & 0x7FFF
        if length_byte_count <= 0 or length_byte_count > 4:
            return None
        if offset + length_byte_count > len(data):
            return None
        length = int.from_bytes(data[offset : offset + length_byte_count], "big")
        offset += length_byte_count
        return length, offset

    return raw_length, offset


def extract_iptc_iim_metadata(path: str | Path) -> dict[str, Any]:
    """Extract mapped IPTC-IIM datasets from any file containing IIM blocks.

    Unknown datasets are ignored. Malformed blocks stop the local scan without
    raising so legacy metadata never interrupts processing.
    """
    file_path = Path(path)
    if file_path.suffix.lower() in RAW_IMAGE_FILE_EXTENSIONS:
        logger.debug("IPTC-IIM full-file scan skipped for RAW file=%s", file_path)
        return {}

    try:
        data = file_path.read_bytes()
    except OSError as exc:
        logger.warning("Failed to read IPTC-IIM for file=%s error=%s", file_path, exc)
        return {}

    fields: dict[str, Any] = {}
    offset = 0
    while True:
        marker_offset = data.find(b"\x1c", offset)
        if marker_offset < 0:
            break
        if marker_offset + 5 > len(data):
            break

        record = data[marker_offset + 1]
        dataset = data[marker_offset + 2]
        length_info = _read_iptc_dataset_length(data, marker_offset + 3)
        if length_info is None:
            offset = marker_offset + 1
            continue

        value_length, value_offset = length_info
        value_end = value_offset + value_length
        if value_end > len(data):
            offset = marker_offset + 1
            continue

        field_name = IPTC_IIM_DATASETS.get((record, dataset))
        if field_name is not None:
            value = _decode_iptc_value(data[value_offset:value_end])
            if value:
                fields[field_name] = value
                fields.setdefault("IPTCIIMFieldSources", {})[
                    field_name
                ] = f"{record}:{dataset}"

        offset = value_end

    return fields


def _extract_xmp_namespace_declarations(packet: str) -> dict[str, str]:
    namespaces: dict[str, str] = {}
    for match in re.finditer(r'\sxmlns:([^=\s]+)=["\']([^"\']+)["\']', packet):
        prefix, uri = match.groups()
        namespaces[prefix] = uri
    return namespaces


def _extract_xmp_packets(data: bytes) -> list[str]:
    packets: list[str] = []
    decoded = data.decode("utf-8", errors="ignore")
    for match in re.finditer(
        r"<x:xmpmeta\b.*?</x:xmpmeta>",
        decoded,
        flags=re.DOTALL,
    ):
        packets.append(match.group(0))
    return packets


def _xmp_text_value(element: ET.Element) -> str:
    texts = [
        text.strip()
        for text in element.itertext()
        if text is not None and text.strip()
    ]
    return normalize_text(" ".join(texts)).value


def _parse_xmp_packet(packet: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    namespaces = _extract_xmp_namespace_declarations(packet)
    if namespaces:
        fields["XMPNamespaces"] = namespaces

    root = ET.fromstring(packet)
    for element in root.iter():
        for raw_name, value in element.attrib.items():
            field_name = _qualified_xmp_name(raw_name)
            if field_name in XMP_RELEVANT_FIELDS and value:
                fields[field_name] = normalize_text(value).value

        field_name = _qualified_xmp_name(element.tag)
        if field_name in XMP_RELEVANT_FIELDS:
            value = _xmp_text_value(element)
            if value:
                fields[field_name] = value

    return fields


def _extract_xmp_metadata_from_bytes(
    data: bytes,
    file_path: Path,
    source_kind: str,
) -> dict[str, Any]:
    packets = _extract_xmp_packets(data)
    if not packets:
        return {}

    fields: dict[str, Any] = {}
    field_sources: dict[str, str] = {}
    for packet in packets:
        try:
            parsed_fields = _parse_xmp_packet(packet)
        except ET.ParseError as exc:
            logger.warning("Failed to parse XMP for file=%s error=%s", file_path, exc)
            continue

        for key, value in parsed_fields.items():
            fields[key] = value
            if key != "XMPNamespaces":
                field_sources[key] = source_kind

    if field_sources:
        fields["XMPFieldSources"] = field_sources
    return fields


def find_xmp_sidecar_path(path: str | Path) -> Path | None:
    """Return the same-basename .xmp sidecar path when it exists."""
    file_path = Path(path)
    sidecar_path = file_path.with_suffix(".xmp")
    if sidecar_path.is_file():
        return sidecar_path
    return None


def _heif_image_info_fields(image: HeifImageInfo) -> dict[str, Any]:
    return {
        "index": image.index,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "primary": image.is_primary,
        "bit_depth": image.bit_depth,
        "metadata_count": image.metadata_count,
        "thumbnail_count": image.thumbnail_count,
        "auxiliary_count": image.auxiliary_count,
        "depth_image_count": image.depth_image_count,
    }


def _heif_container_info_fields(container: HeifContainerInfo) -> dict[str, Any]:
    return {
        "mimetype": container.mimetype,
        "image_count": container.image_count,
        "primary_index": container.primary_index,
        "selected_image_index": container.selected_image_index,
        "is_complex": container.is_complex,
        "unsupported_features": list(container.unsupported_features),
        "warnings": list(container.warnings),
        "images": [_heif_image_info_fields(image) for image in container.images],
    }


def extract_heif_container_metadata(path: str | Path) -> dict[str, Any]:
    """Describe HEIF/HEIC container structure exposed by the backend."""
    file_path = Path(path)
    if file_path.suffix.lower() not in HEIF_IMAGE_FILE_EXTENSIONS:
        return {}

    try:
        container = PillowHeifBackend().read_container_info(file_path)
    except HeifDependencyError as exc:
        logger.warning("HEIF backend unavailable for file=%s: %s", file_path, exc)
        return {
            "status": "unsupported",
            "error": str(exc),
        }
    except HeifBackendError as exc:
        logger.warning("Failed to read HEIF container for file=%s error=%s", file_path, exc)
        return {
            "status": "error",
            "error": str(exc),
        }

    fields = _heif_container_info_fields(container)
    fields["status"] = "complex" if container.is_complex else "supported"
    return fields


def extract_embedded_xmp_metadata(path: str | Path) -> dict[str, Any]:
    """Extract relevant embedded XMP fields from an image file.

    XML/XMP parse failures are logged and return an empty dict so metadata
    issues never abort the organization flow.
    """
    file_path = Path(path)
    if file_path.suffix.lower() in HEIF_IMAGE_FILE_EXTENSIONS:
        try:
            heif_metadata = PillowHeifBackend().read_metadata(file_path)
        except HeifDependencyError as exc:
            logger.warning("HEIF backend unavailable for file=%s: %s", file_path, exc)
            return {}
        except HeifBackendError as exc:
            logger.warning("Failed to read HEIF metadata for file=%s error=%s", file_path, exc)
            return {}
        if not heif_metadata.xmp:
            return {}
        return _extract_xmp_metadata_from_bytes(
            heif_metadata.xmp,
            file_path,
            "embedded",
        )

    if file_path.suffix.lower() in RAW_IMAGE_FILE_EXTENSIONS:
        logger.debug("Embedded XMP scan skipped for RAW file=%s", file_path)
        return {}

    try:
        data = file_path.read_bytes()
    except OSError as exc:
        logger.warning("Failed to read XMP for file=%s error=%s", file_path, exc)
        return {}

    fields = _extract_xmp_metadata_from_bytes(data, file_path, "embedded")
    if file_path.suffix.lower() != ".png":
        return fields

    png_fields = extract_png_metadata(file_path)
    for key, value in png_fields.items():
        if key in {"PNGFieldSources", "tIME"}:
            continue
        parsed_fields = _extract_xmp_metadata_from_bytes(
            value.encode("utf-8"),
            file_path,
            "embedded",
        )
        if not parsed_fields:
            continue

        field_sources = dict(fields.get("XMPFieldSources", {}))
        field_sources.update(parsed_fields.get("XMPFieldSources", {}))
        for parsed_key, parsed_value in parsed_fields.items():
            if parsed_key == "XMPFieldSources":
                continue
            if parsed_key == "XMPNamespaces" and parsed_key in fields:
                fields[parsed_key] = {**fields[parsed_key], **parsed_value}
                continue
            fields[parsed_key] = parsed_value
        if field_sources:
            fields["XMPFieldSources"] = field_sources

    return fields


def extract_xmp_sidecar_metadata(path: str | Path) -> dict[str, Any]:
    """Extract relevant XMP fields from a same-basename .xmp sidecar file."""
    sidecar_path = find_xmp_sidecar_path(path)
    if sidecar_path is None:
        return {}

    try:
        data = sidecar_path.read_bytes()
    except OSError as exc:
        logger.warning("Failed to read XMP sidecar for file=%s error=%s", sidecar_path, exc)
        return {}

    fields = _extract_xmp_metadata_from_bytes(data, sidecar_path, "sidecar")
    if fields:
        fields["XMPSidecarPath"] = str(sidecar_path)
    return fields


def extract_xmp_metadata(path: str | Path) -> dict[str, Any]:
    """Extract relevant embedded and sidecar XMP fields.

    Sidecar XMP uses the same basename as the image with a `.xmp` extension.
    Within the XMP source tier, sidecar values override embedded values because
    they usually represent later external metadata edits. EXIF still has higher
    priority than XMP according to `METADATA_PRECEDENCE_POLICY`.
    """
    embedded_fields = extract_embedded_xmp_metadata(path)
    sidecar_fields = extract_xmp_sidecar_metadata(path)

    if not embedded_fields:
        return sidecar_fields
    if not sidecar_fields:
        return embedded_fields

    merged_fields = dict(embedded_fields)
    embedded_sources = dict(embedded_fields.get("XMPFieldSources", {}))
    sidecar_sources = dict(sidecar_fields.get("XMPFieldSources", {}))
    for key, value in sidecar_fields.items():
        if key == "XMPFieldSources":
            continue
        if key == "XMPNamespaces" and key in merged_fields:
            merged_fields[key] = {**merged_fields[key], **value}
            continue
        merged_fields[key] = value

    merged_sources = {**embedded_sources, **sidecar_sources}
    if merged_sources:
        merged_fields["XMPFieldSources"] = merged_sources
    return merged_fields


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


def _read_exif_value(exif_data: Any, key: int) -> Any:
    """Read one EXIF value without assuming the whole IFD is healthy."""
    try:
        if hasattr(exif_data, "get"):
            return exif_data.get(key)
        return exif_data[key]
    except Exception as exc:
        logger.debug("EXIF tag unavailable: tag=%s error=%s", key, exc)
        return None


def _iter_exif_items(
    exif_data: Any,
    tag_names: dict[int, str],
) -> tuple[list[tuple[int, Any]], bool]:
    """Return EXIF items, falling back to known tags when enumeration fails."""
    if not exif_data:
        return [], False

    if hasattr(exif_data, "items"):
        try:
            return list(exif_data.items()), False
        except Exception as exc:
            logger.warning("Failed to enumerate EXIF IFD; trying known tags: error=%s", exc)

    items: list[tuple[int, Any]] = []
    for key in tag_names:
        value = _read_exif_value(exif_data, key)
        if value is not None:
            items.append((key, value))

    return items, True


def _read_pillow_exif_data(image: Any) -> tuple[Any, bool]:
    """Read EXIF/IFD data from Pillow, including TIFF tag_v2 fallback."""
    try:
        exif_data = image.getexif()
    except Exception as exc:
        logger.warning("Failed to read EXIF IFD from image: error=%s", exc)
        exif_data = None

    if exif_data:
        return exif_data, False

    tag_v2 = getattr(image, "tag_v2", None)
    if tag_v2:
        return tag_v2, True

    tag = getattr(image, "tag", None)
    if tag:
        return tag, True

    return exif_data, False


def _read_pillow_exif_bytes(image_module: Any, exif_bytes: bytes) -> Any:
    """Convert raw EXIF bytes into a Pillow Exif object."""
    exif_data = image_module.Exif()
    exif_data.load(exif_bytes)
    return exif_data


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

    return GPSCoordinates(
        latitude=latitude,
        longitude=longitude,
        provenance=MetadataProvenance(
            source="EXIF",
            field="GPSInfo",
            confidence="high",
            raw_value=gps_info,
        ),
    )


def _extract_xmp_gps_coordinates_from_fields(
    fields: dict[str, Any],
) -> GPSCoordinates | None:
    """Read decimal GPS coordinates from normalized XMP fields."""
    latitude_raw = fields.get("exif:GPSLatitude")
    longitude_raw = fields.get("exif:GPSLongitude")
    field_sources = fields.get("XMPFieldSources", {})
    latitude_source = (
        field_sources.get("exif:GPSLatitude")
        if isinstance(field_sources, dict)
        else None
    )
    longitude_source = (
        field_sources.get("exif:GPSLongitude")
        if isinstance(field_sources, dict)
        else None
    )
    source = (
        "XMP sidecar"
        if "sidecar" in {latitude_source, longitude_source}
        else "XMP"
    )
    latitude = _xmp_gps_to_decimal(
        latitude_raw,
        fields.get("exif:GPSLatitudeRef"),
    )
    longitude = _xmp_gps_to_decimal(
        longitude_raw,
        fields.get("exif:GPSLongitudeRef"),
    )
    if latitude is None or longitude is None:
        return None

    return GPSCoordinates(
        latitude=latitude,
        longitude=longitude,
        provenance=MetadataProvenance(
            source=source,
            field="exif:GPSLatitude,exif:GPSLongitude",
            confidence="medium",
            raw_value={
                "exif:GPSLatitude": latitude_raw,
                "exif:GPSLongitude": longitude_raw,
                "exif:GPSLatitudeRef": fields.get("exif:GPSLatitudeRef"),
                "exif:GPSLongitudeRef": fields.get("exif:GPSLongitudeRef"),
            },
        ),
    )


def _xmp_source_for_field(fields: dict[str, Any], field_name: str) -> str:
    field_sources = fields.get("XMPFieldSources", {})
    source_kind = (
        field_sources.get(field_name)
        if isinstance(field_sources, dict)
        else None
    )
    return "XMP sidecar" if source_kind == "sidecar" else "XMP"


def _normalized_date_candidates_from_exif(
    fields: dict[str, Any],
) -> tuple[MetadataCandidate, ...]:
    candidates: list[MetadataCandidate] = []
    seen_values: set[tuple[datetime, str]] = set()
    for field_name, confidence, precedence_field in EXIF_DATE_FIELD_ALIASES:
        raw_value = fields.get(field_name)
        parsed = _parse_exif_datetime(raw_value)
        if parsed is None:
            continue
        dedupe_key = (parsed, precedence_field)
        if dedupe_key in seen_values:
            continue
        seen_values.add(dedupe_key)
        candidates.append(_datetime_candidate(
            value=parsed,
            source="EXIF",
            field_name=field_name,
            confidence=confidence,
            raw_value=raw_value,
            precedence_field=precedence_field,
        ))
    return tuple(candidates)


def _normalized_date_candidates_from_xmp(
    fields: dict[str, Any],
) -> tuple[MetadataCandidate, ...]:
    candidates: list[MetadataCandidate] = []
    for field_name in ("exif:DateTimeOriginal", "xmp:CreateDate"):
        raw_value = fields.get(field_name)
        parsed = _parse_exif_datetime(raw_value)
        if parsed is None:
            continue
        candidates.append(_datetime_candidate(
            value=parsed,
            source=_xmp_source_for_field(fields, field_name),
            field_name=field_name,
            confidence="medium",
            raw_value=raw_value,
            precedence_source="XMP",
        ))
    return tuple(candidates)


def _normalized_camera_value(
    logical_field: str,
    source: str,
    source_field: str,
    value: Any,
    confidence: MetadataConfidence,
) -> NormalizedMetadataValue | None:
    text = _metadata_text(value)
    if text is None:
        return None
    return NormalizedMetadataValue(
        field=logical_field,
        value=text,
        provenance=MetadataProvenance(
            source=source,
            field=source_field,
            confidence=confidence,
            raw_value=value,
        ),
    )


def _first_normalized_camera_value(
    logical_field: str,
    source: str,
    fields: dict[str, Any],
    source_fields: tuple[str, ...],
    confidence: MetadataConfidence,
) -> NormalizedMetadataValue | None:
    for source_field in source_fields:
        value = fields.get(source_field)
        source_label = (
            _xmp_source_for_field(fields, source_field)
            if source.startswith("XMP")
            else source
        )
        normalized = _normalized_camera_value(
            logical_field,
            source_label,
            source_field,
            value,
            confidence,
        )
        if normalized is not None:
            return normalized
    return None


def _extract_decimal_gps_coordinates_from_fields(
    fields: dict[str, Any],
    *,
    source: str,
    confidence: MetadataConfidence,
) -> GPSCoordinates | None:
    latitude_field = next(
        (
            field_name
            for field_name in ("GPSLatitudeDecimal", "GPSLatitude")
            if field_name in fields
        ),
        None,
    )
    longitude_field = next(
        (
            field_name
            for field_name in ("GPSLongitudeDecimal", "GPSLongitude")
            if field_name in fields
        ),
        None,
    )
    if latitude_field is None or longitude_field is None:
        return None

    latitude = _xmp_gps_to_decimal(fields.get(latitude_field), fields.get("GPSLatitudeRef"))
    longitude = _xmp_gps_to_decimal(
        fields.get(longitude_field),
        fields.get("GPSLongitudeRef"),
    )
    if latitude is None or longitude is None:
        return None

    return GPSCoordinates(
        latitude=latitude,
        longitude=longitude,
        provenance=MetadataProvenance(
            source=source,
            field=f"{latitude_field},{longitude_field}",
            confidence=confidence,
            raw_value={
                latitude_field: fields.get(latitude_field),
                longitude_field: fields.get(longitude_field),
                "GPSLatitudeRef": fields.get("GPSLatitudeRef"),
                "GPSLongitudeRef": fields.get("GPSLongitudeRef"),
            },
        ),
    )


def normalize_metadata_fields(
    *,
    exif_fields: dict[str, Any] | None = None,
    xmp_fields: dict[str, Any] | None = None,
) -> NormalizedImageMetadata:
    """Map heterogeneous source fields to the internal metadata schema.

    The returned values use logical field names such as ``camera_make`` while
    keeping the original source tag in ``MetadataProvenance`` for reports and
    debugging.
    """
    exif_fields = exif_fields or {}
    xmp_fields = xmp_fields or {}

    date_candidates = (
        *_normalized_date_candidates_from_exif(exif_fields),
        *_normalized_date_candidates_from_xmp(xmp_fields),
    )
    camera_make = _first_normalized_camera_value(
        "camera_make",
        "EXIF",
        exif_fields,
        EXIF_CAMERA_MAKE_FIELDS,
        "high",
    )
    camera_model = _first_normalized_camera_value(
        "camera_model",
        "EXIF",
        exif_fields,
        EXIF_CAMERA_MODEL_FIELDS,
        "high",
    )
    if camera_make is None:
        camera_make = _first_normalized_camera_value(
            "camera_make",
            "XMP",
            xmp_fields,
            XMP_CAMERA_MAKE_FIELDS,
            "medium",
        )
    if camera_model is None:
        camera_model = _first_normalized_camera_value(
            "camera_model",
            "XMP",
            xmp_fields,
            XMP_CAMERA_MODEL_FIELDS,
            "medium",
        )

    gps_coordinates = _extract_gps_coordinates_from_fields(exif_fields)
    if gps_coordinates is None:
        gps_coordinates = _extract_decimal_gps_coordinates_from_fields(
            exif_fields,
            source="EXIF",
            confidence="high",
        )
    if gps_coordinates is None:
        gps_coordinates = _extract_xmp_gps_coordinates_from_fields(xmp_fields)

    return NormalizedImageMetadata(
        date_taken_candidates=date_candidates,
        camera_make=camera_make,
        camera_model=camera_model,
        gps_coordinates=gps_coordinates,
    )


def extract_normalized_metadata(path: str | Path) -> NormalizedImageMetadata:
    """Extract metadata and expose it through the internal canonical schema."""
    file_path = Path(path)
    exif_fields = _read_exif_datetime_fields(file_path)
    xmp_fields = extract_xmp_metadata(file_path)
    return normalize_metadata_fields(exif_fields=exif_fields, xmp_fields=xmp_fields)


def validate_reconciliation_policy(policy: str) -> ReconciliationPolicy:
    """Validate and return a supported reconciliation policy."""
    if policy not in RECONCILIATION_POLICY_CHOICES:
        allowed = ", ".join(RECONCILIATION_POLICY_CHOICES)
        raise ValueError(f"Unknown reconciliation policy '{policy}'. Allowed: {allowed}")
    return policy  # type: ignore[return-value]


def _date_rule_index(source: str, field_name: str) -> tuple[int, MetadataSourceRole]:
    for index, rule in enumerate(get_metadata_precedence_policy("date_taken")):
        if rule.source != source:
            continue
        if field_name in rule.keys:
            return index, rule.role
    return len(get_metadata_precedence_policy("date_taken")), "heuristic"


def _datetime_candidate(
    *,
    value: datetime,
    source: str,
    field_name: str,
    confidence: MetadataConfidence,
    raw_value: Any,
    precedence_source: str | None = None,
    precedence_field: str | None = None,
    used_fallback: bool = False,
    date_kind: DateValueKind = "captured",
) -> MetadataCandidate:
    precedence, role = _date_rule_index(
        precedence_source or source,
        precedence_field or field_name,
    )
    return MetadataCandidate(
        value=value,
        provenance=MetadataProvenance(
            source=source,
            field=field_name,
            confidence=confidence,
            raw_value=raw_value,
        ),
        role=role,
        precedence=precedence,
        used_fallback=used_fallback,
        date_kind=date_kind,
    )


def _has_conflicting_candidate_values(candidates: tuple[MetadataCandidate, ...]) -> bool:
    return len({candidate.value for candidate in candidates}) > 1


def reconcile_metadata_candidates(
    field: MetadataFieldName,
    candidates: list[MetadataCandidate],
    policy: ReconciliationPolicy = "precedence",
) -> ReconciliationDecision:
    """Select a candidate according to the configured reconciliation policy."""
    if not candidates:
        raise ValueError("Cannot reconcile metadata without candidates")

    policy = validate_reconciliation_policy(policy)
    ordered_candidates = tuple(
        sorted(candidates, key=lambda candidate: candidate.precedence)
    )

    key_by_policy: dict[ReconciliationPolicy, Callable[[MetadataCandidate], Any]] = {
        "precedence": lambda candidate: candidate.precedence,
        "newest": lambda candidate: (-candidate.value.timestamp(), candidate.precedence)
        if isinstance(candidate.value, datetime)
        else candidate.precedence,
        "oldest": lambda candidate: (candidate.value.timestamp(), candidate.precedence)
        if isinstance(candidate.value, datetime)
        else candidate.precedence,
        "filesystem": lambda candidate: (
            0 if candidate.provenance.source == "filesystem" else 1,
            candidate.precedence,
        ),
    }
    selected = min(ordered_candidates, key=key_by_policy[policy])
    conflict = _has_conflicting_candidate_values(ordered_candidates)
    if policy == "precedence":
        reason = "selected by metadata precedence policy"
    elif policy == "filesystem" and selected.provenance.source == "filesystem":
        reason = "selected by filesystem reconciliation policy"
    elif policy == "filesystem":
        reason = "filesystem value unavailable; selected by metadata precedence policy"
    else:
        reason = f"selected {policy} parsed value, using precedence as tie-breaker"

    return ReconciliationDecision(
        field=field,
        policy=policy,
        selected=selected,
        candidates=ordered_candidates,
        reason=reason,
        conflict=conflict,
    )


def _log_datetime_reconciliation(file_path: Path, decision: ReconciliationDecision) -> None:
    selected = decision.selected.provenance
    candidate_labels = ", ".join(
        f"{candidate.provenance.label}={candidate.value.isoformat()}"
        for candidate in decision.candidates
    )
    if decision.conflict:
        logger.info(
            "Metadata reconciliation conflict: file=%s field=%s policy=%s winner=%s reason=%s candidates=[%s]",
            file_path,
            decision.field,
            decision.policy,
            selected.label,
            decision.reason,
            candidate_labels,
        )
        return

    logger.info(
        "Metadata reconciliation selected: file=%s field=%s policy=%s winner=%s reason=%s",
        file_path,
        decision.field,
        decision.policy,
        selected.label,
        decision.reason,
    )


def _parse_datetime_from_match(
    year: str,
    month: str,
    day: str,
    hour: str = "00",
    minute: str = "00",
    second: str = "00",
) -> datetime | None:
    try:
        parsed = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
        )
    except ValueError:
        return None
    if parsed.year < 1900 or parsed.year > 2100:
        return None
    return parsed


def _parse_datetime_from_text_pattern(text: str) -> tuple[datetime, str] | None:
    normalized = normalize_text(text).value
    patterns = (
        re.compile(
            r"(?<!\d)(?P<year>19\d{2}|20\d{2}|2100)[-_]?"
            r"(?P<month>0[1-9]|1[0-2])[-_]?"
            r"(?P<day>0[1-9]|[12]\d|3[01])"
            r"(?:[T _-]?"
            r"(?P<hour>[01]\d|2[0-3])[-_]?"
            r"(?P<minute>[0-5]\d)[-_]?"
            r"(?P<second>[0-5]\d))?(?!\d)"
        ),
        re.compile(
            r"(?<!\d)(?P<year>19\d{2}|20\d{2}|2100)"
            r"[-_](?P<month>0[1-9]|1[0-2])"
            r"[-_](?P<day>0[1-9]|[12]\d|3[01])(?!\d)"
        ),
    )
    for pattern in patterns:
        match = pattern.search(normalized)
        if match is None:
            continue
        groups = match.groupdict(default="00")
        parsed = _parse_datetime_from_match(
            groups["year"],
            groups["month"],
            groups["day"],
            groups.get("hour", "00"),
            groups.get("minute", "00"),
            groups.get("second", "00"),
        )
        if parsed is not None:
            return parsed, match.group(0)
    return None


def _external_date_sidecar_paths(path: Path) -> tuple[Path, ...]:
    return tuple(
        sidecar_path
        for suffix in (".json", ".txt", ".date")
        for sidecar_path in (path.with_suffix(suffix),)
        if sidecar_path.is_file()
    )


def _iter_json_date_values(value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        results: list[tuple[str, Any]] = []
        for key, item in value.items():
            if key in {
                "date",
                "date_taken",
                "datetime",
                "created_at",
                "DateTimeOriginal",
                "CreateDate",
                "DateCreated",
            }:
                results.append((key, item))
            if isinstance(item, (dict, list)):
                results.extend(_iter_json_date_values(item))
        return results
    if isinstance(value, list):
        results = []
        for item in value:
            results.extend(_iter_json_date_values(item))
        return results
    return []


def _parse_external_sidecar_datetime(path: Path) -> tuple[datetime, str, Any] | None:
    for sidecar_path in _external_date_sidecar_paths(path):
        try:
            text = sidecar_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "Failed to read date sidecar for file=%s sidecar=%s error=%s",
                path,
                sidecar_path,
                exc,
            )
            continue

        if sidecar_path.suffix.lower() == ".json":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                parsed = _parse_datetime_from_text_pattern(text)
                if parsed is not None:
                    value, raw = parsed
                    return value, sidecar_path.name, raw
                continue
            for field_name, raw_value in _iter_json_date_values(payload):
                parsed = _parse_exif_datetime(raw_value)
                if parsed is None and isinstance(raw_value, str):
                    text_parsed = _parse_datetime_from_text_pattern(raw_value)
                    parsed = text_parsed[0] if text_parsed is not None else None
                if parsed is not None:
                    return parsed, f"{sidecar_path.name}:{field_name}", raw_value
            continue

        parsed = _parse_datetime_from_text_pattern(text)
        if parsed is not None:
            value, raw = parsed
            return value, sidecar_path.name, raw

    return None


def _filename_datetime_candidate(path: Path) -> tuple[datetime, str] | None:
    return _parse_datetime_from_text_pattern(path.stem)


def _folder_datetime_candidate(path: Path) -> tuple[datetime, str] | None:
    for parent in path.parents:
        parsed = _parse_datetime_from_text_pattern(parent.name)
        if parsed is not None:
            return parsed
    return None


def _batch_sequence_datetime_candidate(path: Path) -> tuple[datetime, str] | None:
    if not path.parent.is_dir():
        return None
    if re.search(r"\d{2,}", path.stem) is None:
        return None

    sibling_dates: set[datetime] = set()
    try:
        siblings = list(path.parent.iterdir())
    except OSError:
        return None

    for sibling in siblings:
        if sibling == path or sibling.suffix.lower() not in IMAGE_FILE_EXTENSIONS:
            continue
        parsed = _filename_datetime_candidate(sibling)
        if parsed is None:
            parsed = _folder_datetime_candidate(sibling)
        if parsed is not None:
            sibling_dates.add(parsed[0])
        if len(sibling_dates) > 1:
            return None

    if len(sibling_dates) != 1:
        return None
    inferred = next(iter(sibling_dates))
    return inferred, path.parent.name


def _heuristic_datetime_candidates(path: Path) -> list[MetadataCandidate]:
    candidates: list[MetadataCandidate] = []

    sidecar_candidate = _parse_external_sidecar_datetime(path)
    if sidecar_candidate is not None:
        value, field_name, raw_value = sidecar_candidate
        candidates.append(_datetime_candidate(
            value=value,
            source="Sidecar external",
            field_name=field_name,
            confidence="low",
            raw_value=raw_value,
            precedence_field="date_taken",
            used_fallback=True,
            date_kind="inferred",
        ))

    filename_candidate = _filename_datetime_candidate(path)
    if filename_candidate is not None:
        value, raw_value = filename_candidate
        candidates.append(_datetime_candidate(
            value=value,
            source="Filename",
            field_name="date pattern",
            confidence="low",
            raw_value=raw_value,
            used_fallback=True,
            date_kind="inferred",
        ))

    folder_candidate = _folder_datetime_candidate(path)
    if folder_candidate is not None:
        value, raw_value = folder_candidate
        candidates.append(_datetime_candidate(
            value=value,
            source="Folder",
            field_name="date pattern",
            confidence="low",
            raw_value=raw_value,
            used_fallback=True,
            date_kind="inferred",
        ))

    batch_candidate = _batch_sequence_datetime_candidate(path)
    if batch_candidate is not None:
        value, raw_value = batch_candidate
        candidates.append(_datetime_candidate(
            value=value,
            source="Sequence batch",
            field_name="sibling date pattern",
            confidence="low",
            raw_value=raw_value,
            used_fallback=True,
            date_kind="inferred",
        ))

    mtime = path.stat().st_mtime
    candidates.append(_datetime_candidate(
        value=datetime.fromtimestamp(mtime),
        source="filesystem",
        field_name="mtime",
        confidence="low",
        raw_value=mtime,
        precedence_source="Filesystem",
        used_fallback=True,
        date_kind="inferred",
    ))
    return candidates


def _parse_clock_offset(value: str | None) -> int | None:
    """Parse a clock offset string into a total number of seconds.

    Accepted formats:
    - ``+3h`` / ``-3h``  — hours with explicit ``h`` suffix
    - ``+1d`` / ``-1d``  — days (converted to hours × 24)
    - ``+00:30`` / ``-00:30`` — ``HH:MM`` with colon separator
    - ``+3`` / ``-3``    — bare integer treated as hours
    - ``+0:30``          — ``H:MM`` short form

    Returns the offset in seconds, or ``None`` when the value cannot be parsed
    or is out of range.
    """
    if value is None:
        return None
    text = value.strip()

    # Days: [+-]Nd
    day_match = re.fullmatch(r"([+-]?)(\d{1,3})[dD]", text)
    if day_match is not None:
        sign_text, day_text = day_match.groups()
        sign = -1 if sign_text == "-" else 1
        days = int(day_text)
        return sign * days * 24 * 3600

    # Hours with explicit suffix: [+-]Nh
    hour_suffix_match = re.fullmatch(r"([+-]?)(\d{1,4})[hH]", text)
    if hour_suffix_match is not None:
        sign_text, hour_text = hour_suffix_match.groups()
        sign = -1 if sign_text == "-" else 1
        hours = int(hour_text)
        return sign * hours * 3600

    # HH[:MM] — bare hours or hours:minutes
    hm_match = re.fullmatch(r"([+-]?)(\d{1,2})(?::?(\d{2}))?", text)
    if hm_match is None:
        return None
    sign_text, hour_text, minute_text = hm_match.groups()
    sign = -1 if sign_text == "-" else 1
    hours = int(hour_text)
    minutes = int(minute_text or "0")
    if hours > 23 or minutes > 59:
        return None
    return sign * ((hours * 60 + minutes) * 60)


def validate_clock_offset(value: str) -> str:
    """Validate a clock offset string and return it unchanged.

    Raises :class:`ValueError` when the format is not recognised.
    """
    if _parse_clock_offset(value) is None:
        raise ValueError(
            f"Invalid clock offset '{value}'. "
            "Accepted formats: +3h, -1d, +00:30, -5:45, +12."
        )
    return value


def _correction_precedence(priority: str) -> int:
    return {
        "highest": -10,
        "metadata": 2,
        "heuristic": 5,
    }.get(priority, -10)


def _correction_datetime_candidates(
    correction: CorrectionApplication | None,
    base_candidates: list[MetadataCandidate],
) -> list[MetadataCandidate]:
    if correction is None:
        return []

    candidates: list[MetadataCandidate] = []
    precedence = _correction_precedence(correction.priority)
    field_name = ",".join(correction.selectors) or correction.source_path.name
    raw_base = {
        "manifest": str(correction.source_path),
        "selectors": correction.selectors,
        "timezone": correction.timezone,
    }

    if correction.date_value is not None:
        parsed = _parse_exif_datetime(correction.date_value)
        if parsed is None:
            text_parsed = _parse_datetime_from_text_pattern(correction.date_value)
            parsed = text_parsed[0] if text_parsed is not None else None
        if parsed is not None:
            candidates.append(MetadataCandidate(
                value=parsed,
                provenance=MetadataProvenance(
                    source="Correction manifest",
                    field=field_name,
                    confidence="high",
                    raw_value={**raw_base, "date": correction.date_value},
                ),
                role="primary" if correction.priority == "highest" else "fallback",
                precedence=precedence,
                used_fallback=False,
                date_kind="captured",
            ))

    offset_seconds = _parse_clock_offset(correction.clock_offset)
    if offset_seconds is not None and base_candidates:
        base_decision = reconcile_metadata_candidates(
            "date_taken",
            base_candidates,
            "precedence",
        )
        adjusted_value = datetime.fromtimestamp(
            base_decision.selected.value.timestamp() + offset_seconds
        )
        candidates.append(MetadataCandidate(
            value=adjusted_value,
            provenance=MetadataProvenance(
                source="Correction manifest",
                field=field_name,
                confidence="high",
                raw_value={
                    **raw_base,
                    "clock_offset": correction.clock_offset,
                    "base_source": base_decision.selected.provenance.label,
                    "base_value": base_decision.selected.value.isoformat(),
                },
            ),
            role="primary" if correction.priority == "highest" else "fallback",
            precedence=precedence,
            used_fallback=False,
            date_kind="captured",
        ))

    return candidates


def extract_iptc_iim_location(path: str | Path) -> tuple[dict[str, str], MetadataProvenance] | None:
    """Return IPTC-IIM city/state/country fields with provenance when present."""
    fields = extract_iptc_iim_metadata(path)
    location = {
        "city": fields.get("City"),
        "state": fields.get("Province-State"),
        "country": fields.get("Country-PrimaryLocationName"),
    }
    if all(value is None for value in location.values()):
        return None

    raw_value = {
        key: value
        for key, value in {
            "City": fields.get("City"),
            "Province-State": fields.get("Province-State"),
            "Country-PrimaryLocationName": fields.get("Country-PrimaryLocationName"),
        }.items()
        if value is not None
    }
    return location, MetadataProvenance(
        source="IPTC-IIM",
        field="2:90,2:95,2:101",
        confidence="medium",
        raw_value=raw_value,
    )


def extract_xmp_textual_location(
    path: str | Path,
) -> tuple[dict[str, str], MetadataProvenance] | None:
    """Return XMP textual city/state/country fields with provenance when present."""
    fields = extract_xmp_metadata(path)
    location = {
        "city": fields.get("photoshop:City"),
        "state": fields.get("photoshop:State"),
        "country": fields.get("photoshop:Country"),
    }
    if all(value is None for value in location.values()):
        return None

    raw_value = {
        key: value
        for key, value in {
            "photoshop:City": fields.get("photoshop:City"),
            "photoshop:State": fields.get("photoshop:State"),
            "photoshop:Country": fields.get("photoshop:Country"),
        }.items()
        if value is not None
    }
    field_sources = fields.get("XMPFieldSources", {})
    source = (
        "XMP sidecar"
        if isinstance(field_sources, dict)
        and any(field_sources.get(key) == "sidecar" for key in raw_value)
        else "XMP"
    )
    return location, MetadataProvenance(
        source=source,
        field="photoshop:City,photoshop:State,photoshop:Country",
        confidence="low",
        raw_value=raw_value,
    )


def _external_location_sidecar_paths(path: Path) -> tuple[Path, ...]:
    return tuple(
        sidecar_path
        for suffix in (".location.json", ".json", ".location", ".txt")
        for sidecar_path in (path.with_suffix(suffix),)
        if sidecar_path.is_file()
    )


def _location_from_manifest_payload(payload: Any) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    location_payload = payload.get("location")
    if isinstance(location_payload, dict):
        payload = location_payload
    location = {
        "city": payload.get("city") or payload.get("City"),
        "state": payload.get("state") or payload.get("State"),
        "country": payload.get("country") or payload.get("Country"),
    }
    if all(value is None for value in location.values()):
        return None
    return location


def extract_external_location_manifest(
    path: str | Path,
) -> tuple[dict[str, str], MetadataProvenance] | None:
    """Return location from a same-basename external manifest when present."""
    file_path = Path(path)
    for sidecar_path in _external_location_sidecar_paths(file_path):
        try:
            text = sidecar_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "Failed to read location sidecar for file=%s sidecar=%s error=%s",
                file_path,
                sidecar_path,
                exc,
            )
            continue

        location = None
        if sidecar_path.suffix.lower() == ".json":
            try:
                location = _location_from_manifest_payload(json.loads(text))
            except json.JSONDecodeError:
                location = None
        if location is None:
            location = _parse_location_text(text)
        if location is None:
            continue

        return location, MetadataProvenance(
            source="External manifest",
            field=sidecar_path.name,
            confidence="low",
            raw_value=location,
        )
    return None


def _parse_location_text(text: str) -> dict[str, str] | None:
    cleaned = normalize_text(text).value.strip()
    if not cleaned or re.fullmatch(r"\d{4}[-_/]?\d{2}[-_/]?\d{2}", cleaned):
        return None
    if cleaned.lower().startswith(("pytest-", "pytest_", "tmp", "test_")):
        return None

    parts = [
        part.strip(" .")
        for part in re.split(r"\s*[,/]\s*", cleaned)
        if part.strip()
    ]
    if parts and not all(re.search(r"[^\W\d_]", part) for part in parts):
        return None
    if len(parts) >= 3:
        return {"city": parts[0], "state": parts[1], "country": parts[2]}
    if len(parts) == 2:
        return {"city": parts[0], "state": parts[1], "country": None}

    dash_parts = [part.strip(" .") for part in cleaned.split("-") if part.strip()]
    if (
        len(dash_parts) == 2
        and all(re.search(r"[^\W\d_]", part) for part in dash_parts)
    ):
        return {"city": dash_parts[0], "state": dash_parts[1], "country": None}

    return None


def infer_location_from_folder(
    path: str | Path,
) -> tuple[dict[str, str], MetadataProvenance] | None:
    """Infer location from parent folder or album names."""
    file_path = Path(path)
    for parent in file_path.parents:
        location = _parse_location_text(parent.name)
        if location is None:
            continue
        return location, MetadataProvenance(
            source="Folder",
            field=parent.name,
            confidence="low",
            raw_value=parent.name,
        )
    return None


def infer_location_from_batch(
    path: str | Path,
) -> tuple[dict[str, str], MetadataProvenance] | None:
    """Infer location from sibling manifest context when the batch is consistent."""
    file_path = Path(path)
    if not file_path.parent.is_dir():
        return None
    locations: list[dict[str, str]] = []
    try:
        siblings = list(file_path.parent.iterdir())
    except OSError:
        return None
    for sibling in siblings:
        if sibling == file_path or sibling.suffix.lower() not in IMAGE_FILE_EXTENSIONS:
            continue
        manifest_location = extract_external_location_manifest(sibling)
        if manifest_location is not None:
            locations.append(manifest_location[0])
        if len({tuple(sorted(item.items())) for item in locations}) > 1:
            return None
    if len(locations) != 1:
        return None
    return locations[0], MetadataProvenance(
        source="Batch",
        field="sibling manifest",
        confidence="low",
        raw_value=locations[0],
    )


def infer_textual_location(
    path: str | Path,
) -> tuple[dict[str, str], MetadataProvenance] | None:
    """Infer non-GPS location from textual metadata and safe external context."""
    for resolver in (
        extract_iptc_iim_location,
        extract_xmp_textual_location,
        extract_external_location_manifest,
        infer_location_from_folder,
        infer_location_from_batch,
    ):
        location = resolver(path)
        if location is not None:
            return location
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
    if file_path.suffix.lower() not in EXIF_IMAGE_FILE_EXTENSIONS:
        logger.debug(
            "EXIF extraction skipped for unsupported metadata format: file=%s",
            file_path,
        )
        return {}

    if file_path.suffix.lower() in RAW_IMAGE_FILE_EXTENSIONS:
        return _extract_raw_exif_metadata(file_path)

    try:
        from PIL import ExifTags, Image
    except ImportError:
        logger.debug("Pillow not available; EXIF extraction skipped for file=%s", file_path)
        return {}

    try:
        used_container_fallback = False
        if file_path.suffix.lower() in HEIF_IMAGE_FILE_EXTENSIONS:
            heif_backend = PillowHeifBackend()
            heif_metadata = heif_backend.read_metadata(file_path)
            if heif_metadata.exif:
                exif_data = _read_pillow_exif_bytes(Image, heif_metadata.exif)
            else:
                with heif_backend.open(file_path) as image:
                    exif_data, used_container_fallback = _read_pillow_exif_data(image)
        else:
            with Image.open(file_path) as image:
                exif_data, used_container_fallback = _read_pillow_exif_data(image)
    except HeifDependencyError as exc:
        logger.warning("HEIF backend unavailable for file=%s: %s", file_path, exc)
        return {}
    except HeifBackendError as exc:
        logger.warning("Failed to read HEIF metadata for file=%s error=%s", file_path, exc)
        return {}
    except Exception as exc:
        logger.warning("Fatal EXIF read error for file=%s error=%s", file_path, exc)
        return {}

    if not exif_data:
        logger.debug("EXIF metadata absent for file=%s", file_path)
        return {}

    fields: dict[str, Any] = {}
    exif_tags = {**FALLBACK_EXIF_TAGS, **getattr(ExifTags, "TAGS", {})}
    gps_tags = getattr(ExifTags, "GPSTAGS", {})
    exif_items, used_tag_fallback = _iter_exif_items(exif_data, exif_tags)
    if not exif_items:
        logger.debug("EXIF metadata absent for file=%s", file_path)
        return {}
    if used_container_fallback:
        logger.debug("EXIF read using container tag fallback for file=%s", file_path)
    if used_tag_fallback:
        logger.warning(
            "Partial EXIF metadata recovered after inconsistent IFD for file=%s",
            file_path,
        )

    for key, value in exif_items:
        tag_name = exif_tags.get(key)
        if isinstance(tag_name, str):
            if tag_name == "GPSInfo":
                value = _normalize_gps_info(value, gps_tags)
                if not value:
                    value = _normalize_gps_info(_read_gps_ifd(exif_data, key), gps_tags)
            if value not in (None, {}, ""):
                if isinstance(value, (str, bytes)):
                    value = normalize_text(value).value
                fields[tag_name] = value

    gps_coordinates = _extract_gps_coordinates_from_fields(fields)
    if gps_coordinates is not None:
        fields["GPSLatitudeDecimal"] = gps_coordinates.latitude
        fields["GPSLongitudeDecimal"] = gps_coordinates.longitude

    return fields


def _extract_raw_exif_metadata(file_path: Path) -> dict[str, Any]:
    """Extract EXIF-compatible metadata from a RAW-family file."""
    try:
        fields = TiffRawMetadataBackend().read_metadata(file_path).fields
    except RawMetadataError as exc:
        logger.warning("Failed to read RAW metadata for file=%s error=%s", file_path, exc)
        return {}

    normalized_fields: dict[str, Any] = {}
    for key, value in fields.items():
        if value in (None, {}, ""):
            continue
        if isinstance(value, (str, bytes)):
            value = normalize_text(value).value
        normalized_fields[key] = value

    gps_coordinates = _extract_gps_coordinates_from_fields(normalized_fields)
    if gps_coordinates is not None:
        normalized_fields["GPSLatitudeDecimal"] = gps_coordinates.latitude
        normalized_fields["GPSLongitudeDecimal"] = gps_coordinates.longitude

    if not normalized_fields:
        logger.debug("RAW metadata absent for file=%s", file_path)
    return normalized_fields


def _metadata_text(value: Any) -> str | None:
    if value is None:
        return None
    text = normalize_text(value).value if isinstance(value, bytes) else str(value)
    text = normalize_text(text).value.strip("\x00").strip()
    return text or None


def extract_camera_profile(path: str | Path) -> dict[str, str]:
    """Return camera make/model metadata for correction manifest matching."""
    file_path = Path(path)
    normalized = normalize_metadata_fields(
        exif_fields=extract_exif_metadata(file_path),
        xmp_fields=extract_xmp_metadata(file_path),
    )
    make = (
        str(normalized.camera_make.value)
        if normalized.camera_make is not None
        else None
    )
    model = (
        str(normalized.camera_model.value)
        if normalized.camera_model is not None
        else None
    )

    profile = " ".join(part for part in (make, model) if part)
    result: dict[str, str] = {}
    if make:
        result["make"] = make
    if model:
        result["model"] = model
    if profile:
        result["profile"] = profile
    return result


def extract_gps_coordinates(path: str | Path) -> GPSCoordinates | None:
    """Extract GPS coordinates in decimal degrees when available."""
    normalized = normalize_metadata_fields(
        exif_fields=extract_exif_metadata(path),
        xmp_fields=extract_xmp_metadata(path),
    )
    return normalized.gps_coordinates


def resolve_best_available_datetime(
    path: str | Path,
    reconciliation_policy: ReconciliationPolicy = "precedence",
    date_heuristics: bool = DATE_HEURISTICS_DEFAULT,
    correction: CorrectionApplication | None = None,
) -> DateTimeResolution:
    """Return the best available datetime plus fallback metadata.

    The default reconciliation policy applies `METADATA_PRECEDENCE_POLICY`.
    Other policies can choose newest, oldest or filesystem values while still
    using the precedence matrix as deterministic tie-breaker. When enabled,
    heuristic candidates are marked as inferred and use low confidence.
    """
    file_path = Path(path)
    reconciliation_policy = validate_reconciliation_policy(reconciliation_policy)
    candidates: list[MetadataCandidate] = []
    exif_fields = _read_exif_datetime_fields(file_path)
    xmp_fields = extract_xmp_metadata(file_path)
    normalized = normalize_metadata_fields(
        exif_fields=exif_fields,
        xmp_fields=xmp_fields,
    )
    candidates.extend(normalized.date_taken_candidates)

    iptc_fields = extract_iptc_iim_metadata(file_path)
    raw_date = iptc_fields.get("DateCreated")
    parsed = _parse_iptc_datetime(raw_date, iptc_fields.get("TimeCreated"))
    if parsed is not None:
        raw_value = {
            "DateCreated": raw_date,
            "TimeCreated": iptc_fields.get("TimeCreated"),
        }
        candidates.append(_datetime_candidate(
            value=parsed,
            source="IPTC-IIM",
            field_name="2:55,2:60",
            confidence="medium",
            raw_value={
                key: value for key, value in raw_value.items() if value is not None
            },
            precedence_field="DateCreated",
        ))

    png_fields = extract_png_metadata(file_path)
    for field_name in ("Creation Time", "CreationTime"):
        raw_value = png_fields.get(field_name)
        parsed = _parse_exif_datetime(raw_value)
        if parsed is not None:
            candidates.append(_datetime_candidate(
                value=parsed,
                source="PNG metadata",
                field_name=field_name,
                confidence="medium",
                raw_value=raw_value,
            ))

    raw_png_time = png_fields.get("tIME") if date_heuristics else None
    parsed_png_time = _parse_exif_datetime(raw_png_time)
    if parsed_png_time is not None:
        candidates.append(_datetime_candidate(
            value=parsed_png_time,
            source="PNG metadata",
            field_name="tIME",
            confidence="low",
            raw_value=raw_png_time,
            used_fallback=True,
            date_kind="inferred",
        ))

    candidates.extend(_correction_datetime_candidates(correction, candidates))

    if date_heuristics and (not candidates or reconciliation_policy == "filesystem"):
        candidates.extend(_heuristic_datetime_candidates(file_path))
    elif not candidates:
        raise ValueError("No usable date metadata and date heuristics are disabled")

    decision = reconcile_metadata_candidates(
        "date_taken",
        candidates,
        reconciliation_policy,
    )
    _log_datetime_reconciliation(file_path, decision)
    selected = decision.selected
    if selected.provenance.source == "filesystem":
        logger.info(
            "Datetime fallback to file modification time for file=%s source=%s field=%s confidence=%s",
            file_path,
            selected.provenance.source,
            selected.provenance.field,
            selected.provenance.confidence,
        )
    return DateTimeResolution(
        value=selected.value,
        used_fallback=selected.used_fallback,
        provenance=selected.provenance,
        reconciliation=decision,
        date_kind=selected.date_kind,
    )


def get_best_available_datetime(path: str | Path) -> datetime:
    """Return the best available datetime for a file."""
    return resolve_best_available_datetime(path).value
