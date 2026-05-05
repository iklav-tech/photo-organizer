"""Synthetic legacy metadata corpus used by automated tests."""

from __future__ import annotations

import binascii
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import zlib


XMP_TEMPLATE = """<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
      xmlns:xmp="http://ns.adobe.com/xap/1.0/"
      xmp:CreateDate="{date}" />
  </rdf:RDF>
</x:xmpmeta>"""


@dataclass(frozen=True)
class MetadataCorpusCase:
    """One generated fixture plus the expected resolved date provenance."""

    case_id: str
    description: str
    relative_path: str
    expected_value: datetime | None
    expected_source: str | None
    expected_field: str | None
    expected_confidence: str | None
    writer: Callable[[Path], Path]
    expect_conflict: bool = False


def _iptc_dataset(record: int, dataset: int, value: str) -> bytes:
    raw_value = value.encode("utf-8")
    return (
        b"\x1c"
        + bytes([record, dataset])
        + len(raw_value).to_bytes(2, "big")
        + raw_value
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return len(data).to_bytes(4, "big") + chunk_type + data + crc.to_bytes(4, "big")


def _minimal_png_with_chunks(*chunks: tuple[bytes, bytes]) -> bytes:
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    for chunk_type, data in chunks:
        png += _png_chunk(chunk_type, data)
    png += _png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
    png += _png_chunk(b"IEND", b"")
    return png


def _save_rgb_image(path: Path, *, exif=None) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1, 1), color=(8, 16, 24))
    if exif is None:
        image.save(path)
    else:
        image.save(path, exif=exif)


def _write_jpeg_exif(path: Path) -> Path:
    from PIL import Image

    exif = Image.Exif()
    exif[36867] = "2024:01:02 03:04:05"
    _save_rgb_image(path, exif=exif)
    return path


def _write_tiff_tags(path: Path) -> Path:
    from PIL import Image, TiffImagePlugin

    path.parent.mkdir(parents=True, exist_ok=True)
    tiffinfo = TiffImagePlugin.ImageFileDirectory_v2()
    tiffinfo[306] = "2021:06:07 08:09:10"
    Image.new("RGB", (1, 1), color=(8, 16, 24)).save(path, tiffinfo=tiffinfo)
    return path


def _write_iptc_iim(path: Path) -> Path:
    _save_rgb_image(path)
    with path.open("ab") as image_file:
        image_file.write(_iptc_dataset(2, 55, "20240815"))
        image_file.write(_iptc_dataset(2, 60, "143209"))
        image_file.write(_iptc_dataset(2, 90, "Paraty"))
    return path


def _write_embedded_xmp(path: Path) -> Path:
    _save_rgb_image(path)
    with path.open("ab") as image_file:
        image_file.write(XMP_TEMPLATE.format(date="2022-03-04T05:06:07").encode())
    return path


def _write_xmp_sidecar(path: Path) -> Path:
    _save_rgb_image(path)
    path.with_suffix(".xmp").write_text(
        XMP_TEMPLATE.format(date="2023-04-05T06:07:08"),
        encoding="utf-8",
    )
    return path


def _write_png_exif(path: Path) -> Path:
    from PIL import Image

    exif = Image.Exif()
    exif[36867] = "2020:02:03 04:05:06"
    _save_rgb_image(path, exif=exif)
    return path


def _write_png_text(path: Path) -> Path:
    xmp_packet = XMP_TEMPLATE.format(date="2024-08-15T14:32:09").encode()
    itxt = (
        b"XML:com.adobe.xmp\x00"
        b"\x00\x00"
        b"\x00"
        b"\x00"
        + xmp_packet
    )
    text = b"Creation Time\x002024:08:15 14:32:09"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_minimal_png_with_chunks((b"iTXt", itxt), (b"tEXt", text)))
    return path


def _write_without_metadata(path: Path) -> Path:
    _save_rgb_image(path)
    return path


def _write_conflicting_metadata(path: Path) -> Path:
    from PIL import Image

    exif = Image.Exif()
    exif[36867] = "2020:01:02 03:04:05"
    _save_rgb_image(path, exif=exif)
    with path.open("ab") as image_file:
        image_file.write(XMP_TEMPLATE.format(date="2024-08-15T14:32:09").encode())
    return path


METADATA_CORPUS_CASES: tuple[MetadataCorpusCase, ...] = (
    MetadataCorpusCase(
        case_id="jpeg_exif",
        description="JPEG with EXIF DateTimeOriginal",
        relative_path="jpeg-exif/image.jpg",
        expected_value=datetime(2024, 1, 2, 3, 4, 5),
        expected_source="EXIF",
        expected_field="DateTimeOriginal",
        expected_confidence="high",
        writer=_write_jpeg_exif,
    ),
    MetadataCorpusCase(
        case_id="tiff_tags",
        description="TIFF container DateTime tag",
        relative_path="tiff-tags/image.tif",
        expected_value=datetime(2021, 6, 7, 8, 9, 10),
        expected_source="EXIF",
        expected_field="CreateDate",
        expected_confidence="medium",
        writer=_write_tiff_tags,
    ),
    MetadataCorpusCase(
        case_id="iptc_iim",
        description="JPEG carrying IPTC-IIM date datasets",
        relative_path="iptc-iim/image.jpg",
        expected_value=datetime(2024, 8, 15, 14, 32, 9),
        expected_source="IPTC-IIM",
        expected_field="2:55,2:60",
        expected_confidence="medium",
        writer=_write_iptc_iim,
    ),
    MetadataCorpusCase(
        case_id="xmp_embedded",
        description="JPEG with embedded XMP packet",
        relative_path="xmp-embedded/image.jpg",
        expected_value=datetime(2022, 3, 4, 5, 6, 7),
        expected_source="XMP",
        expected_field="xmp:CreateDate",
        expected_confidence="medium",
        writer=_write_embedded_xmp,
    ),
    MetadataCorpusCase(
        case_id="xmp_sidecar",
        description="JPEG with same-basename XMP sidecar",
        relative_path="xmp-sidecar/image.jpg",
        expected_value=datetime(2023, 4, 5, 6, 7, 8),
        expected_source="XMP sidecar",
        expected_field="xmp:CreateDate",
        expected_confidence="medium",
        writer=_write_xmp_sidecar,
    ),
    MetadataCorpusCase(
        case_id="png_exif",
        description="PNG with eXIf date metadata",
        relative_path="png-exif/image.png",
        expected_value=datetime(2020, 2, 3, 4, 5, 6),
        expected_source="EXIF",
        expected_field="DateTimeOriginal",
        expected_confidence="high",
        writer=_write_png_exif,
    ),
    MetadataCorpusCase(
        case_id="png_itxt_text",
        description="PNG with iTXt XMP and tEXt Creation Time",
        relative_path="png-text/image.png",
        expected_value=datetime(2024, 8, 15, 14, 32, 9),
        expected_source="XMP",
        expected_field="xmp:CreateDate",
        expected_confidence="medium",
        writer=_write_png_text,
    ),
    MetadataCorpusCase(
        case_id="no_metadata",
        description="JPEG without usable metadata",
        relative_path="no-metadata/image.jpg",
        expected_value=None,
        expected_source=None,
        expected_field=None,
        expected_confidence=None,
        writer=_write_without_metadata,
    ),
    MetadataCorpusCase(
        case_id="conflicting_metadata",
        description="JPEG with conflicting EXIF and XMP dates",
        relative_path="conflicting/image.jpg",
        expected_value=datetime(2020, 1, 2, 3, 4, 5),
        expected_source="EXIF",
        expected_field="DateTimeOriginal",
        expected_confidence="high",
        writer=_write_conflicting_metadata,
        expect_conflict=True,
    ),
)


def build_metadata_corpus(root: Path) -> dict[str, Path]:
    """Generate all corpus files under *root* and return paths by case id."""
    return {
        case.case_id: case.writer(root / case.relative_path)
        for case in METADATA_CORPUS_CASES
    }
