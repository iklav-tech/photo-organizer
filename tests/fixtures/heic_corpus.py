"""Synthetic HEIC corpus used by automated tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class HeicCorpus:
    """Generated HEIC sample paths."""

    with_exif_gps: Path
    with_exif_no_gps: Path
    without_exif: Path
    malformed: Path


def _save_heic(path: Path, *, exif=None) -> Path:
    from PIL import Image
    import pillow_heif

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (8, 8), color=(32, 64, 96))
    if exif is not None:
        image.info["exif"] = exif.tobytes()
    pillow_heif.from_pillow(image).save(path)
    return path


def _iphone_like_exif(*, include_gps: bool):
    from PIL import Image

    exif = Image.Exif()
    exif[271] = "Apple"
    exif[272] = "iPhone 15"
    exif[274] = 1
    exif[36867] = "2024:05:06 07:08:09"
    if include_gps:
        exif[34853] = {
            1: "S",
            2: (23.0, 30.0, 0.0),
            3: "W",
            4: (46.0, 37.0, 30.0),
        }
    return exif


def ensure_heic_writer_available(tmp_path: Path) -> None:
    """Raise RuntimeError when pillow-heif/libheif cannot write a tiny HEIC."""
    probe = tmp_path / "probe.heic"
    try:
        _save_heic(probe)
    except Exception as exc:  # pragma: no cover - platform dependent
        raise RuntimeError(f"HEIC writer unavailable: {exc}") from exc


def build_heic_corpus(root: Path) -> HeicCorpus:
    """Generate common iPhone-like HEIC samples under *root*."""
    with_exif_gps = _save_heic(
        root / "iphone-exif-gps" / "IMG_0001.HEIC",
        exif=_iphone_like_exif(include_gps=True),
    )
    with_exif_no_gps = _save_heic(
        root / "iphone-exif-no-gps" / "IMG_0002.HEIC",
        exif=_iphone_like_exif(include_gps=False),
    )
    without_exif = _save_heic(root / "iphone-no-exif" / "IMG_0003.HEIC")
    malformed = root / "malformed" / "IMG_0004.HEIC"
    malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_bytes(b"not-a-real-heic")
    return HeicCorpus(
        with_exif_gps=with_exif_gps,
        with_exif_no_gps=with_exif_no_gps,
        without_exif=without_exif,
        malformed=malformed,
    )


EXPECTED_HEIC_DATETIME = datetime(2024, 5, 6, 7, 8, 9)
