"""Shared package constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageFormat:
    """Configuration for one supported image file format."""

    name: str
    extensions: frozenset[str]
    supports_exif: bool = False


# Add new image formats here so scanner, hashing and metadata behavior remain
# aligned from a single configuration point.
IMAGE_FORMATS = (
    ImageFormat("JPEG", frozenset({".jpg", ".jpeg"}), supports_exif=True),
    ImageFormat("PNG", frozenset({".png"}), supports_exif=True),
    ImageFormat("TIFF", frozenset({".tif", ".tiff"}), supports_exif=True),
    ImageFormat("WEBP", frozenset({".webp"})),
    ImageFormat("BMP", frozenset({".bmp"})),
    ImageFormat("HEIF", frozenset({".heic", ".heif", ".hif"}), supports_exif=True),
    ImageFormat("Canon RAW", frozenset({".cr2", ".cr3", ".crw"}), supports_exif=True),
    ImageFormat("Nikon RAW", frozenset({".nef"}), supports_exif=True),
    ImageFormat("Sony RAW", frozenset({".arw"}), supports_exif=True),
    ImageFormat("Panasonic RAW", frozenset({".rw2"}), supports_exif=True),
    ImageFormat("Olympus/OM System RAW", frozenset({".orf"}), supports_exif=True),
    ImageFormat("Fujifilm RAW", frozenset({".raf"}), supports_exif=True),
)

IMAGE_FILE_EXTENSIONS = frozenset(
    extension
    for image_format in IMAGE_FORMATS
    for extension in image_format.extensions
)
EXIF_IMAGE_FILE_EXTENSIONS = frozenset(
    extension
    for image_format in IMAGE_FORMATS
    if image_format.supports_exif
    for extension in image_format.extensions
)
HEIF_IMAGE_FILE_EXTENSIONS = frozenset(
    extension
    for image_format in IMAGE_FORMATS
    if image_format.name == "HEIF"
    for extension in image_format.extensions
)
RAW_IMAGE_FILE_EXTENSIONS = frozenset(
    extension
    for image_format in IMAGE_FORMATS
    if image_format.name.endswith("RAW")
    for extension in image_format.extensions
)


def supported_image_extensions_text() -> str:
    """Return a stable comma-separated list of supported image extensions."""
    return ", ".join(sorted(IMAGE_FILE_EXTENSIONS))
