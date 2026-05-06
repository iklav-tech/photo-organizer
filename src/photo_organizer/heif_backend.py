"""Optional HEIF/HEIC image backend integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


HEIF_INSTALL_HINT = (
    "HEIF/HEIC metadata extraction requires pillow-heif and its native libheif "
    "support. Install project dependencies with `pip install -e .` or "
    "`pip install -r requirements.txt`; on Linux, ensure libheif is available "
    "from the OS package manager when needed."
)


class HeifBackendError(RuntimeError):
    """Base error raised by HEIF backend integrations."""


class HeifDependencyError(HeifBackendError):
    """Raised when optional HEIF dependencies are unavailable."""


@dataclass(frozen=True)
class HeifMetadata:
    """Raw metadata extracted from a HEIF/HEIC container."""

    exif: bytes | None = None
    xmp: bytes | None = None
    metadata: tuple[dict[str, Any], ...] = ()


@runtime_checkable
class HeifBackend(Protocol):
    """Backend capable of opening HEIF/HEIC files as Pillow images."""

    def open(self, path: str | Path):
        """Return a Pillow-compatible image object for *path*."""

    def read_metadata(self, path: str | Path) -> HeifMetadata:
        """Return raw HEIF metadata without requiring callers to know backend APIs."""


class PillowHeifBackend:
    """HEIF backend implemented through pillow-heif/libheif."""

    def _load_pillow_heif(self):
        try:
            import pillow_heif
        except (ImportError, OSError) as exc:
            raise HeifDependencyError(HEIF_INSTALL_HINT) from exc

        try:
            pillow_heif.register_heif_opener()
        except (ImportError, OSError, RuntimeError) as exc:
            raise HeifDependencyError(HEIF_INSTALL_HINT) from exc

        return pillow_heif

    def open(self, path: str | Path):
        self._load_pillow_heif()
        from PIL import Image

        return Image.open(path)

    def read_metadata(self, path: str | Path) -> HeifMetadata:
        pillow_heif = self._load_pillow_heif()
        try:
            heif_file = pillow_heif.open_heif(path)
        except (ValueError, EOFError, SyntaxError, RuntimeError, OSError) as exc:
            raise HeifBackendError(f"Failed to open HEIF metadata: {exc}") from exc

        info = getattr(heif_file, "info", {}) or {}
        exif = info.get("exif")
        xmp = info.get("xmp")
        metadata = info.get("metadata") or ()
        return HeifMetadata(
            exif=exif if isinstance(exif, bytes) else None,
            xmp=xmp if isinstance(xmp, bytes) else None,
            metadata=tuple(item for item in metadata if isinstance(item, dict)),
        )
