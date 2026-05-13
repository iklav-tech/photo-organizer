"""Synthetic RAW metadata corpus used by automated tests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import struct


@dataclass(frozen=True)
class RawCorpusCase:
    """One generated RAW-family fixture and its expected normalized metadata."""

    case_id: str
    description: str
    relative_path: str
    raw_format: str
    make: str
    model: str
    expected_datetime: datetime
    expected_latitude: float | None
    expected_longitude: float | None
    writer: Callable[[Path, "RawCorpusCase"], Path]


def _write_tiff_entry(
    data: bytearray,
    entry_offset: int,
    tag: int,
    type_id: int,
    count: int,
    value_or_offset: int,
) -> None:
    struct.pack_into("<HHII", data, entry_offset, tag, type_id, count, value_or_offset)


def _append_tiff_ascii(data: bytearray, value: str) -> tuple[int, int]:
    raw = value.encode("utf-8") + b"\x00"
    offset = len(data)
    data.extend(raw)
    return offset, len(raw)


def _append_tiff_rationals(
    data: bytearray,
    values: tuple[tuple[int, int], ...],
) -> tuple[int, int]:
    offset = len(data)
    for numerator, denominator in values:
        data.extend(struct.pack("<II", numerator, denominator))
    return offset, len(values)


def _minimal_raw_tiff_bytes(
    *,
    make: str,
    model: str,
    datetime_original: str = "2024:05:06 07:08:09",
    include_gps: bool = True,
) -> bytes:
    main_entries = 5 if include_gps else 4
    data = bytearray(b"II*\x00\x08\x00\x00\x00")

    main_ifd_offset = 8
    main_ifd_size = 2 + main_entries * 12 + 4
    data.extend(b"\x00" * main_ifd_size)
    struct.pack_into("<H", data, main_ifd_offset, main_entries)

    make_offset, make_count = _append_tiff_ascii(data, make)
    model_offset, model_count = _append_tiff_ascii(data, model)
    datetime_offset, datetime_count = _append_tiff_ascii(data, "2024:01:02 03:04:05")

    exif_ifd_offset = len(data)
    exif_entries = 1
    exif_ifd_size = 2 + exif_entries * 12 + 4
    data.extend(b"\x00" * exif_ifd_size)
    struct.pack_into("<H", data, exif_ifd_offset, exif_entries)
    original_offset, original_count = _append_tiff_ascii(data, datetime_original)
    _write_tiff_entry(
        data,
        exif_ifd_offset + 2,
        36867,
        2,
        original_count,
        original_offset,
    )

    gps_ifd_offset = 0
    if include_gps:
        gps_ifd_offset = len(data)
        gps_entries = 4
        gps_ifd_size = 2 + gps_entries * 12 + 4
        data.extend(b"\x00" * gps_ifd_size)
        struct.pack_into("<H", data, gps_ifd_offset, gps_entries)
        latitude_offset, latitude_count = _append_tiff_rationals(
            data,
            ((23, 1), (30, 1), (0, 1)),
        )
        longitude_offset, longitude_count = _append_tiff_rationals(
            data,
            ((46, 1), (37, 1), (30, 1)),
        )
        _write_tiff_entry(data, gps_ifd_offset + 2, 1, 2, 2, ord("S"))
        _write_tiff_entry(data, gps_ifd_offset + 14, 2, 5, latitude_count, latitude_offset)
        _write_tiff_entry(data, gps_ifd_offset + 26, 3, 2, 2, ord("W"))
        _write_tiff_entry(
            data,
            gps_ifd_offset + 38,
            4,
            5,
            longitude_count,
            longitude_offset,
        )

    _write_tiff_entry(data, main_ifd_offset + 2, 271, 2, make_count, make_offset)
    _write_tiff_entry(data, main_ifd_offset + 14, 272, 2, model_count, model_offset)
    _write_tiff_entry(data, main_ifd_offset + 26, 306, 2, datetime_count, datetime_offset)
    _write_tiff_entry(data, main_ifd_offset + 38, 34665, 4, 1, exif_ifd_offset)
    if include_gps:
        _write_tiff_entry(data, main_ifd_offset + 50, 34853, 4, 1, gps_ifd_offset)

    return bytes(data)


def minimal_raw_tiff_bytes(
    *,
    make: str = "Canon",
    model: str = "EOS R5",
    include_gps: bool = True,
) -> bytes:
    """Return a minimal TIFF-style RAW byte stream for performance tests."""
    return _minimal_raw_tiff_bytes(
        make=make,
        model=model,
        include_gps=include_gps,
    )


def _write_valid_raw(path: Path, case: RawCorpusCase) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_minimal_raw_tiff_bytes(make=case.make, model=case.model))
    return path


def _write_no_gps_raw(path: Path, case: RawCorpusCase) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        _minimal_raw_tiff_bytes(
            make=case.make,
            model=case.model,
            include_gps=False,
        )
    )
    return path


def _write_corrupt_raw(path: Path, _case: RawCorpusCase) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not a raw tiff stream")
    return path


RAW_CORPUS_VALID_CASES: tuple[RawCorpusCase, ...] = (
    RawCorpusCase(
        case_id="apple_proraw_dng",
        description="Apple ProRAW DNG with TIFF-style EXIF metadata",
        relative_path="apple-proraw/IMG_0001.dng",
        raw_format="Apple ProRAW",
        make="Apple",
        model="iPhone 15 Pro",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="canon_cr2",
        description="Canon CR2 with TIFF-style EXIF metadata",
        relative_path="canon/IMG_0001.cr2",
        raw_format="Canon RAW",
        make="Canon",
        model="EOS R5",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="canon_cr3",
        description="Canon CR3 with TIFF-style EXIF metadata",
        relative_path="canon/IMG_0002.cr3",
        raw_format="Canon RAW",
        make="Canon",
        model="EOS R6 Mark II",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="canon_crw",
        description="Canon CRW with TIFF-style EXIF metadata",
        relative_path="canon/IMG_0003.crw",
        raw_format="Canon RAW",
        make="Canon",
        model="PowerShot G5",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="nikon_nef",
        description="Nikon NEF with TIFF-style EXIF metadata",
        relative_path="nikon/DSC_0001.nef",
        raw_format="Nikon RAW",
        make="NIKON CORPORATION",
        model="NIKON Z 6",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="sony_arw",
        description="Sony ARW with TIFF-style EXIF metadata",
        relative_path="sony/DSC00001.arw",
        raw_format="Sony RAW",
        make="SONY",
        model="ILCE-7M4",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="panasonic_rw2",
        description="Panasonic RW2 with TIFF-style EXIF metadata",
        relative_path="panasonic/P1000001.rw2",
        raw_format="Panasonic RAW",
        make="Panasonic",
        model="DC-GH6",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="olympus_orf",
        description="Olympus ORF with TIFF-style EXIF metadata",
        relative_path="olympus/P5010001.orf",
        raw_format="Olympus/OM System RAW",
        make="OM Digital Solutions",
        model="OM-1",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
    RawCorpusCase(
        case_id="fujifilm_raf",
        description="Fujifilm RAF with TIFF-style EXIF metadata",
        relative_path="fujifilm/DSCF0001.raf",
        raw_format="Fujifilm RAW",
        make="FUJIFILM",
        model="X-T5",
        expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
        expected_latitude=-23.5,
        expected_longitude=-46.625,
        writer=_write_valid_raw,
    ),
)

RAW_CORPUS_NO_GPS_CASE = RawCorpusCase(
    case_id="canon_cr2_no_gps",
    description="Canon CR2 with valid date/camera metadata and no GPS IFD",
    relative_path="edge-cases/no-gps.cr2",
    raw_format="Canon RAW",
    make="Canon",
    model="EOS R5",
    expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
    expected_latitude=None,
    expected_longitude=None,
    writer=_write_no_gps_raw,
)

RAW_CORPUS_CORRUPT_CASE = RawCorpusCase(
    case_id="sony_arw_corrupt",
    description="Sony ARW with unreadable RAW/TIFF metadata",
    relative_path="edge-cases/corrupt.arw",
    raw_format="Sony RAW",
    make="",
    model="",
    expected_datetime=datetime(2024, 5, 6, 7, 8, 9),
    expected_latitude=None,
    expected_longitude=None,
    writer=_write_corrupt_raw,
)

RAW_CORPUS_CASES: tuple[RawCorpusCase, ...] = (
    *RAW_CORPUS_VALID_CASES,
    RAW_CORPUS_NO_GPS_CASE,
    RAW_CORPUS_CORRUPT_CASE,
)


def build_raw_corpus(root: Path) -> dict[str, Path]:
    """Generate all RAW corpus files under *root* and return paths by case id."""
    return {
        case.case_id: case.writer(root / case.relative_path, case)
        for case in RAW_CORPUS_CASES
    }
