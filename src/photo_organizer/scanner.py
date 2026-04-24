"""File scanning utilities for image discovery."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def is_supported_image_file(path: str | Path) -> bool:
    """Return True when the file extension is supported."""
    candidate = Path(path)
    return candidate.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def find_image_files(directory: str | Path, recursive: bool = True) -> list[Path]:
    """Find supported image files in a directory.

    The result is always sorted to keep a stable and predictable order.
    """
    root = Path(directory)

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root}")

    pattern_iterator = root.rglob("*") if recursive else root.glob("*")

    found = [
        path
        for path in pattern_iterator
        if path.is_file() and is_supported_image_file(path)
    ]

    return sorted(found, key=lambda path: str(path))
