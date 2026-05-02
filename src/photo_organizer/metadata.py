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
import logging
from pathlib import Path
import re
from typing import Any, Literal
import xml.etree.ElementTree as ET
import zlib

from photo_organizer.constants import EXIF_IMAGE_FILE_EXTENSIONS


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


@dataclass(frozen=True)
class GPSCoordinates:
    """Resolved GPS coordinates in decimal degrees."""

    latitude: float
    longitude: float
    provenance: MetadataProvenance | None = dataclass_field(
        default=None,
        compare=False,
    )


XMP_NAMESPACE_PREFIXES = {
    "http://ns.adobe.com/xap/1.0/": "xmp",
    "http://ns.adobe.com/exif/1.0/": "exif",
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
        date_value = date_value.decode("utf-8", errors="ignore")
    if not isinstance(date_value, str):
        return None

    date_text = date_value.strip()
    if not re.fullmatch(r"\d{8}", date_text):
        return None

    time_text = "000000"
    if isinstance(time_value, bytes):
        time_value = time_value.decode("utf-8", errors="ignore")
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
        ref = ref.decode("ascii", errors="ignore")
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
        value = value.decode("utf-8", errors="ignore")
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
    for encoding in ("utf-8", "latin-1"):
        try:
            return value.decode(encoding).strip("\x00").strip()
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace").strip("\x00").strip()


def _decode_png_latin1(value: bytes) -> str:
    return value.decode("latin-1").strip("\x00").strip()


def _decode_png_utf8(value: bytes) -> str:
    return value.decode("utf-8", errors="replace").strip("\x00").strip()


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
    return " ".join(texts)


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
                fields[field_name] = value

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


def extract_embedded_xmp_metadata(path: str | Path) -> dict[str, Any]:
    """Extract relevant embedded XMP fields from an image file.

    XML/XMP parse failures are logged and return an empty dict so metadata
    issues never abort the organization flow.
    """
    file_path = Path(path)
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
            exif_data, used_container_fallback = _read_pillow_exif_data(image)
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
                fields[tag_name] = value

    gps_coordinates = _extract_gps_coordinates_from_fields(fields)
    if gps_coordinates is not None:
        fields["GPSLatitudeDecimal"] = gps_coordinates.latitude
        fields["GPSLongitudeDecimal"] = gps_coordinates.longitude

    return fields


def extract_gps_coordinates(path: str | Path) -> GPSCoordinates | None:
    """Extract GPS coordinates in decimal degrees when available."""
    exif_coordinates = _extract_gps_coordinates_from_fields(extract_exif_metadata(path))
    if exif_coordinates is not None:
        return exif_coordinates
    return _extract_xmp_gps_coordinates_from_fields(extract_xmp_metadata(path))


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
        raw_value = exif_fields.get(field_name)
        parsed = _parse_exif_datetime(raw_value)
        if parsed is not None:
            confidence: MetadataConfidence = (
                "high" if field_name == "DateTimeOriginal" else "medium"
            )
            provenance = MetadataProvenance(
                source="EXIF",
                field=field_name,
                confidence=confidence,
                raw_value=raw_value,
            )
            logger.info(
                "Datetime resolved: file=%s source=%s field=%s confidence=%s",
                file_path,
                provenance.source,
                provenance.field,
                provenance.confidence,
            )
            return DateTimeResolution(
                value=parsed,
                used_fallback=False,
                provenance=provenance,
            )

    xmp_fields = extract_xmp_metadata(file_path)
    for field_name in ("exif:DateTimeOriginal", "xmp:CreateDate"):
        raw_value = xmp_fields.get(field_name)
        parsed = _parse_exif_datetime(raw_value)
        if parsed is not None:
            field_sources = xmp_fields.get("XMPFieldSources", {})
            source_kind = (
                field_sources.get(field_name)
                if isinstance(field_sources, dict)
                else None
            )
            provenance = MetadataProvenance(
                source="XMP sidecar" if source_kind == "sidecar" else "XMP",
                field=field_name,
                confidence="medium",
                raw_value=raw_value,
            )
            logger.info(
                "Datetime resolved: file=%s source=%s field=%s confidence=%s",
                file_path,
                provenance.source,
                provenance.field,
                provenance.confidence,
            )
            return DateTimeResolution(
                value=parsed,
                used_fallback=False,
                provenance=provenance,
            )

    iptc_fields = extract_iptc_iim_metadata(file_path)
    raw_date = iptc_fields.get("DateCreated")
    parsed = _parse_iptc_datetime(raw_date, iptc_fields.get("TimeCreated"))
    if parsed is not None:
        raw_value = {
            "DateCreated": raw_date,
            "TimeCreated": iptc_fields.get("TimeCreated"),
        }
        provenance = MetadataProvenance(
            source="IPTC-IIM",
            field="2:55,2:60",
            confidence="medium",
            raw_value={
                key: value for key, value in raw_value.items() if value is not None
            },
        )
        logger.info(
            "Datetime resolved: file=%s source=%s field=%s confidence=%s",
            file_path,
            provenance.source,
            provenance.field,
            provenance.confidence,
        )
        return DateTimeResolution(
            value=parsed,
            used_fallback=False,
            provenance=provenance,
        )

    png_fields = extract_png_metadata(file_path)
    for field_name in ("Creation Time", "CreationTime"):
        raw_value = png_fields.get(field_name)
        parsed = _parse_exif_datetime(raw_value)
        if parsed is not None:
            provenance = MetadataProvenance(
                source="PNG metadata",
                field=field_name,
                confidence="medium",
                raw_value=raw_value,
            )
            logger.info(
                "Datetime resolved: file=%s source=%s field=%s confidence=%s",
                file_path,
                provenance.source,
                provenance.field,
                provenance.confidence,
            )
            return DateTimeResolution(
                value=parsed,
                used_fallback=False,
                provenance=provenance,
            )

    raw_png_time = png_fields.get("tIME")
    parsed_png_time = _parse_exif_datetime(raw_png_time)
    if parsed_png_time is not None:
        provenance = MetadataProvenance(
            source="PNG metadata",
            field="tIME",
            confidence="low",
            raw_value=raw_png_time,
        )
        logger.info(
            "Datetime secondary fallback: file=%s source=%s field=%s confidence=%s",
            file_path,
            provenance.source,
            provenance.field,
            provenance.confidence,
        )
        return DateTimeResolution(
            value=parsed_png_time,
            used_fallback=True,
            provenance=provenance,
        )

    mtime = file_path.stat().st_mtime
    provenance = MetadataProvenance(
        source="filesystem",
        field="mtime",
        confidence="low",
        raw_value=mtime,
    )
    logger.info(
        "Datetime fallback to file modification time for file=%s source=%s field=%s confidence=%s",
        file_path,
        provenance.source,
        provenance.field,
        provenance.confidence,
    )
    return DateTimeResolution(
        value=datetime.fromtimestamp(mtime),
        used_fallback=True,
        provenance=provenance,
    )


def get_best_available_datetime(path: str | Path) -> datetime:
    """Return the best available datetime for a file."""
    return resolve_best_available_datetime(path).value
