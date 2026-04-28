"""File hashing utilities for safe image comparison."""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from photo_organizer.scanner import find_image_files, is_supported_image_file


DEFAULT_HASH_ALGORITHM = "sha256"
DEFAULT_CHUNK_SIZE = 1024 * 1024

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DuplicateGroup:
    """A group of files with identical content."""

    content_hash: str
    original: Path
    duplicates: tuple[Path, ...]


def calculate_file_hash(
    path: str | Path,
    *,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    """Calculate a deterministic hexadecimal hash for a file.

    The file is read in fixed-size chunks so large files are not loaded into
    memory at once.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    digest = hashlib.new(algorithm)
    with file_path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(chunk_size), b""):
            digest.update(chunk)

    return digest.hexdigest()


def calculate_image_hash(
    path: str | Path,
    *,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    """Calculate a deterministic hash for a supported image file."""
    file_path = Path(path)
    if not is_supported_image_file(file_path):
        raise ValueError(f"Unsupported image file extension: {file_path.suffix}")

    return calculate_file_hash(
        file_path,
        algorithm=algorithm,
        chunk_size=chunk_size,
    )


def file_hashes_match(
    first_path: str | Path,
    second_path: str | Path,
    *,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bool:
    """Return True when two files have the same hash using safe comparison."""
    first_hash = calculate_file_hash(
        first_path,
        algorithm=algorithm,
        chunk_size=chunk_size,
    )
    second_hash = calculate_file_hash(
        second_path,
        algorithm=algorithm,
        chunk_size=chunk_size,
    )

    return hmac.compare_digest(first_hash, second_hash)


def image_hashes_match(
    first_path: str | Path,
    second_path: str | Path,
    *,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bool:
    """Return True when two supported image files have the same hash."""
    first_hash = calculate_image_hash(
        first_path,
        algorithm=algorithm,
        chunk_size=chunk_size,
    )
    second_hash = calculate_image_hash(
        second_path,
        algorithm=algorithm,
        chunk_size=chunk_size,
    )

    return hmac.compare_digest(first_hash, second_hash)


def find_duplicate_images(
    paths: Iterable[str | Path],
    *,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[DuplicateGroup]:
    """Identify supported image files with identical content.

    The first file in stable path order is treated as the original. Remaining
    files in the same hash bucket are reported as duplicates.
    """
    hashes_by_path: dict[Path, str] = {}

    for path in sorted((Path(candidate) for candidate in paths), key=lambda item: str(item)):
        if not is_supported_image_file(path):
            continue

        try:
            hashes_by_path[path] = calculate_image_hash(
                path,
                algorithm=algorithm,
                chunk_size=chunk_size,
            )
        except Exception as exc:
            logger.error(
                "Failed to calculate image hash: file=%s error=%s",
                path,
                exc,
            )
            continue

    paths_by_hash: dict[str, list[Path]] = {}
    for path, content_hash in hashes_by_path.items():
        paths_by_hash.setdefault(content_hash, []).append(path)

    groups: list[DuplicateGroup] = []
    for content_hash, grouped_paths in paths_by_hash.items():
        if len(grouped_paths) < 2:
            continue

        groups.append(
            DuplicateGroup(
                content_hash=content_hash,
                original=grouped_paths[0],
                duplicates=tuple(grouped_paths[1:]),
            )
        )

    return groups


def find_duplicate_image_groups(
    directory: str | Path,
    *,
    recursive: bool = True,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[DuplicateGroup]:
    """Find duplicate supported image groups inside a directory."""
    return find_duplicate_images(
        find_image_files(directory, recursive=recursive),
        algorithm=algorithm,
        chunk_size=chunk_size,
    )
