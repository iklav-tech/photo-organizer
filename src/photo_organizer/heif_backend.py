"""Optional HEIF/HEIC image backend integration."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


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


@runtime_checkable
class HeifBackend(Protocol):
    """Backend capable of opening HEIF/HEIC files as Pillow images."""

    def open(self, path: str | Path):
        """Return a Pillow-compatible image object for *path*."""


class PillowHeifBackend:
    """HEIF backend implemented through pillow-heif/libheif."""

    def open(self, path: str | Path):
        try:
            import pillow_heif
        except (ImportError, OSError) as exc:
            raise HeifDependencyError(HEIF_INSTALL_HINT) from exc

        try:
            pillow_heif.register_heif_opener()
        except (ImportError, OSError, RuntimeError) as exc:
            raise HeifDependencyError(HEIF_INSTALL_HINT) from exc

        from PIL import Image

        return Image.open(path)
