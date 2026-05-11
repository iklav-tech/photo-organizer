"""Safe metadata reader for proprietary RAW files.

The first RAW backend intentionally implements a focused EXIF/TIFF reader
instead of a full RAW decoder. Many proprietary RAW formats in the initial
scope expose capture metadata through TIFF Image File Directories, which is
enough for organization decisions without decoding image pixels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Any


class RawMetadataError(RuntimeError):
    """Raised when RAW metadata cannot be parsed safely."""


@dataclass(frozen=True)
class RawMetadata:
    """Normalized metadata extracted from a RAW file."""

    fields: dict[str, Any]


class TiffRawMetadataBackend:
    """Read EXIF-style metadata from TIFF-based RAW files."""

    _TYPE_SIZES = {
        1: 1,   # BYTE
        2: 1,   # ASCII
        3: 2,   # SHORT
        4: 4,   # LONG
        5: 8,   # RATIONAL
        7: 1,   # UNDEFINED
        9: 4,   # SLONG
        10: 8,  # SRATIONAL
    }

    _TAGS = {
        271: "Make",
        272: "Model",
        306: "DateTime",
        34665: "ExifIFDPointer",
        34853: "GPSInfo",
    }
    _EXIF_TAGS = {
        36867: "DateTimeOriginal",
        36868: "DateTimeDigitized",
    }
    _GPS_TAGS = {
        1: "GPSLatitudeRef",
        2: "GPSLatitude",
        3: "GPSLongitudeRef",
        4: "GPSLongitude",
    }

    def read_metadata(self, path: str | Path) -> RawMetadata:
        file_path = Path(path)
        try:
            data = file_path.read_bytes()
        except OSError as exc:
            raise RawMetadataError(f"Failed to read RAW file: {exc}") from exc

        try:
            return RawMetadata(fields=self._parse_tiff_metadata(data))
        except (struct.error, ValueError, IndexError) as exc:
            raise RawMetadataError(f"Failed to parse RAW metadata: {exc}") from exc

    def _parse_tiff_metadata(self, data: bytes) -> dict[str, Any]:
        endian = self._byte_order(data)
        first_ifd_offset = self._first_ifd_offset(data, endian)
        fields = self._read_ifd_fields(data, first_ifd_offset, endian, self._TAGS)

        exif_offset = fields.pop("ExifIFDPointer", None)
        if isinstance(exif_offset, int):
            fields.update(
                self._read_ifd_fields(data, exif_offset, endian, self._EXIF_TAGS)
            )

        gps_offset = fields.get("GPSInfo")
        if isinstance(gps_offset, int):
            gps_info = self._read_ifd_fields(data, gps_offset, endian, self._GPS_TAGS)
            if gps_info:
                fields["GPSInfo"] = gps_info
            else:
                fields.pop("GPSInfo", None)

        return {key: value for key, value in fields.items() if value not in (None, "")}

    @staticmethod
    def _byte_order(data: bytes) -> str:
        if len(data) < 8:
            raise ValueError("RAW file is too small for TIFF metadata")
        marker = data[:2]
        if marker == b"II":
            endian = "<"
        elif marker == b"MM":
            endian = ">"
        else:
            raise ValueError("RAW file does not expose TIFF byte order")
        magic = struct.unpack_from(f"{endian}H", data, 2)[0]
        if magic not in {42, 43, 85}:
            raise ValueError(f"Unsupported TIFF magic: {magic}")
        return endian

    @staticmethod
    def _first_ifd_offset(data: bytes, endian: str) -> int:
        offset = struct.unpack_from(f"{endian}I", data, 4)[0]
        if offset <= 0 or offset >= len(data):
            raise ValueError("Invalid first IFD offset")
        return offset

    def _read_ifd_fields(
        self,
        data: bytes,
        offset: int,
        endian: str,
        tag_names: dict[int, str],
    ) -> dict[str, Any]:
        if offset < 0 or offset + 2 > len(data):
            raise ValueError("Invalid IFD offset")

        entry_count = struct.unpack_from(f"{endian}H", data, offset)[0]
        entries_offset = offset + 2
        fields: dict[str, Any] = {}
        for index in range(entry_count):
            entry_offset = entries_offset + index * 12
            if entry_offset + 12 > len(data):
                break
            tag, type_id, count, value_or_offset = struct.unpack_from(
                f"{endian}HHII",
                data,
                entry_offset,
            )
            field_name = tag_names.get(tag)
            if field_name is None:
                continue
            value = self._read_entry_value(data, endian, type_id, count, value_or_offset)
            if value not in (None, "", (), []):
                fields[field_name] = value

        return fields

    def _read_entry_value(
        self,
        data: bytes,
        endian: str,
        type_id: int,
        count: int,
        value_or_offset: int,
    ) -> Any:
        type_size = self._TYPE_SIZES.get(type_id)
        if type_size is None or count <= 0:
            return None

        byte_count = type_size * count
        if byte_count <= 4:
            raw = struct.pack(f"{endian}I", value_or_offset)[:byte_count]
        else:
            if value_or_offset < 0 or value_or_offset + byte_count > len(data):
                return None
            raw = data[value_or_offset : value_or_offset + byte_count]

        if type_id == 2:
            return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()
        if type_id in {1, 7}:
            values = tuple(raw)
            return values[0] if count == 1 else values
        if type_id == 3:
            values = struct.unpack(f"{endian}{count}H", raw)
            return values[0] if count == 1 else values
        if type_id == 4:
            values = struct.unpack(f"{endian}{count}I", raw)
            return values[0] if count == 1 else values
        if type_id == 5:
            return self._read_rationals(raw, endian, count, signed=False)
        if type_id == 9:
            values = struct.unpack(f"{endian}{count}i", raw)
            return values[0] if count == 1 else values
        if type_id == 10:
            return self._read_rationals(raw, endian, count, signed=True)
        return None

    @staticmethod
    def _read_rationals(
        raw: bytes,
        endian: str,
        count: int,
        *,
        signed: bool,
    ) -> tuple[tuple[int, int], ...] | tuple[int, int]:
        fmt = "ii" if signed else "II"
        values = tuple(
            struct.unpack_from(f"{endian}{fmt}", raw, index * 8)
            for index in range(count)
        )
        return values[0] if count == 1 else values
