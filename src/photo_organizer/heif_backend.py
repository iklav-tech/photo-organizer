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


@dataclass(frozen=True)
class HeifImageInfo:
    """Describes one image entry exposed by a HEIF backend."""

    index: int
    width: int | None = None
    height: int | None = None
    mode: str | None = None
    is_primary: bool = False
    bit_depth: int | None = None
    metadata_count: int = 0
    thumbnail_count: int = 0
    auxiliary_count: int = 0
    depth_image_count: int = 0


@dataclass(frozen=True)
class HeifContainerInfo:
    """Backend-neutral description of a HEIF/HEIC container."""

    mimetype: str | None = None
    image_count: int | None = None
    primary_index: int | None = None
    selected_image_index: int | None = None
    images: tuple[HeifImageInfo, ...] = ()
    unsupported_features: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_complex(self) -> bool:
        """Return whether the file has structure beyond a single primary image."""
        return bool(self.unsupported_features)


@runtime_checkable
class HeifBackend(Protocol):
    """Backend capable of opening HEIF/HEIC files as Pillow images."""

    def open(self, path: str | Path):
        """Return a Pillow-compatible image object for *path*."""

    def read_metadata(self, path: str | Path) -> HeifMetadata:
        """Return raw HEIF metadata without requiring callers to know backend APIs."""

    def read_container_info(self, path: str | Path) -> HeifContainerInfo:
        """Return a backend-neutral description of the HEIF container."""


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
        heif_file = self._open_heif_file(path)
        selected_image, _selected_index, _warnings = self._select_primary_image(heif_file)
        info = getattr(selected_image, "info", {}) or getattr(heif_file, "info", {}) or {}
        exif = info.get("exif")
        xmp = info.get("xmp")
        metadata = info.get("metadata") or ()
        return HeifMetadata(
            exif=exif if isinstance(exif, bytes) else None,
            xmp=xmp if isinstance(xmp, bytes) else None,
            metadata=tuple(item for item in metadata if isinstance(item, dict)),
        )

    def read_container_info(self, path: str | Path) -> HeifContainerInfo:
        heif_file = self._open_heif_file(path)
        images = self._image_entries(heif_file)
        _selected_image, selected_index, selection_warnings = self._select_primary_image(
            heif_file,
        )
        image_infos = tuple(
            self._image_info(image, index)
            for index, image in enumerate(images)
        )
        unsupported_features = self._unsupported_features(image_infos)
        return HeifContainerInfo(
            mimetype=getattr(heif_file, "mimetype", None),
            image_count=len(images),
            primary_index=self._primary_index(heif_file),
            selected_image_index=selected_index,
            images=image_infos,
            unsupported_features=unsupported_features,
            warnings=selection_warnings,
        )

    def _open_heif_file(self, path: str | Path):
        pillow_heif = self._load_pillow_heif()
        try:
            return pillow_heif.open_heif(path)
        except (ValueError, EOFError, SyntaxError, RuntimeError, OSError) as exc:
            raise HeifBackendError(f"Failed to open HEIF container: {exc}") from exc

    @staticmethod
    def _image_entries(heif_file) -> tuple[Any, ...]:
        try:
            images = tuple(heif_file)
        except TypeError:
            images = tuple(getattr(heif_file, "_images", ()) or ())
        if images:
            return images
        return (heif_file,)

    @staticmethod
    def _primary_index(heif_file) -> int | None:
        value = getattr(heif_file, "primary_index", None)
        return value if isinstance(value, int) and value >= 0 else None

    def _select_primary_image(self, heif_file) -> tuple[Any, int, tuple[str, ...]]:
        images = self._image_entries(heif_file)
        primary_flags = [
            index
            for index, image in enumerate(images)
            if bool((getattr(image, "info", {}) or {}).get("primary"))
        ]
        if len(primary_flags) == 1:
            return images[primary_flags[0]], primary_flags[0], ()
        if len(primary_flags) > 1:
            return (
                images[primary_flags[0]],
                primary_flags[0],
                ("multiple primary image flags; selected the lowest index",),
            )

        primary_index = self._primary_index(heif_file)
        if primary_index is not None and primary_index < len(images):
            return images[primary_index], primary_index, ()

        return (
            images[0],
            0,
            ("primary image not exposed by backend; selected image index 0",),
        )

    @staticmethod
    def _count_info_items(info: dict[str, Any], key: str) -> int:
        value = info.get(key)
        if isinstance(value, dict):
            return len(value)
        if isinstance(value, (list, tuple)):
            return len(value)
        return 0

    def _image_info(self, image, index: int) -> HeifImageInfo:
        info = getattr(image, "info", {}) or {}
        size = getattr(image, "size", None)
        width = height = None
        if isinstance(size, tuple) and len(size) == 2:
            width, height = size
        bit_depth = info.get("bit_depth")
        return HeifImageInfo(
            index=index,
            width=width if isinstance(width, int) else None,
            height=height if isinstance(height, int) else None,
            mode=getattr(image, "mode", None),
            is_primary=bool(info.get("primary")),
            bit_depth=bit_depth if isinstance(bit_depth, int) else None,
            metadata_count=self._count_info_items(info, "metadata"),
            thumbnail_count=self._count_info_items(info, "thumbnails"),
            auxiliary_count=self._count_info_items(info, "aux"),
            depth_image_count=self._count_info_items(info, "depth_images"),
        )

    @staticmethod
    def _unsupported_features(images: tuple[HeifImageInfo, ...]) -> tuple[str, ...]:
        features: list[str] = []
        if len(images) > 1:
            features.append("multiple images or sequence: only the selected primary image is processed")
        if any(image.thumbnail_count for image in images):
            features.append("embedded thumbnails: not extracted")
        if any(image.auxiliary_count for image in images):
            features.append("auxiliary images: not extracted")
        if any(image.depth_image_count for image in images):
            features.append("depth images: not extracted")
        return tuple(features)
