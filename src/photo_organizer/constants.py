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
