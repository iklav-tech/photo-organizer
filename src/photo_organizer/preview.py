"""Optional image preview generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from photo_organizer.constants import HEIF_IMAGE_FILE_EXTENSIONS
from photo_organizer.heif_backend import HeifBackend, PillowHeifBackend


DEFAULT_HEIC_PREVIEW_SIZE = 512
DEFAULT_HEIC_PREVIEW_QUALITY = 85


class PreviewGenerationError(RuntimeError):
    """Raised when an optional preview cannot be generated."""


def is_heif_image(path: str | Path) -> bool:
    """Return whether *path* points to a supported HEIF/HEIC extension."""
    return Path(path).suffix.lower() in HEIF_IMAGE_FILE_EXTENSIONS


def build_heic_preview_destination(
    image_path: str | Path,
    preview_root: str | Path | None = None,
) -> Path:
    """Return the default JPEG preview path for a HEIF/HEIC image."""
    path = Path(image_path)
    parent = Path(preview_root) if preview_root is not None else path.parent / ".previews"
    return parent / f"{path.stem}.jpg"


def _prepare_jpeg_image(image: Any) -> Any:
    if getattr(image, "mode", None) == "RGB":
        return image
    return image.convert("RGB")


def generate_heic_preview(
    source: str | Path,
    destination: str | Path,
    *,
    max_size: int = DEFAULT_HEIC_PREVIEW_SIZE,
    quality: int = DEFAULT_HEIC_PREVIEW_QUALITY,
    backend: HeifBackend | None = None,
) -> Path | None:
    """Generate a JPEG preview for a HEIF/HEIC file.

    Returns the preview path when a preview was written and ``None`` when the
    source extension is not a supported HEIF/HEIC extension.
    """
    source_path = Path(source)
    if not is_heif_image(source_path):
        return None
    if max_size <= 0:
        raise PreviewGenerationError("max_size must be greater than zero")
    if not 1 <= quality <= 100:
        raise PreviewGenerationError("quality must be between 1 and 100")

    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    selected_backend = backend or PillowHeifBackend()

    image = None
    try:
        image = selected_backend.open(source_path)
        preview = image.copy()
        preview.thumbnail((max_size, max_size))
        preview = _prepare_jpeg_image(preview)
        preview.save(destination_path, format="JPEG", quality=quality)
    except Exception as exc:
        raise PreviewGenerationError(f"Failed to generate HEIC preview: {exc}") from exc
    finally:
        if image is not None and hasattr(image, "close"):
            image.close()

    return destination_path
