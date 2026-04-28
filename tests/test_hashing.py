from pathlib import Path
from typing import Any

import pytest

from photo_organizer import hashing


def test_calculate_image_hash_is_deterministic(tmp_path: Path) -> None:
    file_path = tmp_path / "photo.jpg"
    file_path.write_bytes(b"same image bytes")

    first_hash = hashing.calculate_image_hash(file_path)
    second_hash = hashing.calculate_image_hash(file_path)

    assert first_hash == second_hash


def test_calculate_image_hash_matches_sha256_expected_value(tmp_path: Path) -> None:
    file_path = tmp_path / "photo.png"
    file_path.write_bytes(b"image bytes")

    result = hashing.calculate_image_hash(file_path)

    assert result == "de7030234493a8bea844dbe1d8676e68a2c1a4b014c721f0425a22b6df66faec"


def test_calculate_file_hash_reads_in_chunks(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "large.jpg"
    content = b"abcdefghij"
    file_path.write_bytes(content)
    read_sizes: list[int] = []

    original_open = Path.open

    def tracking_open(self: Path, *args: Any, **kwargs: Any):
        file_obj = original_open(self, *args, **kwargs)

        class TrackingFile:
            def __enter__(self):
                file_obj.__enter__()
                return self

            def __exit__(self, exc_type, exc, tb):
                return file_obj.__exit__(exc_type, exc, tb)

            def read(self, size: int = -1) -> bytes:
                read_sizes.append(size)
                if size == -1 or size > 4:
                    raise AssertionError("file was not read in bounded chunks")
                return file_obj.read(size)

        return TrackingFile()

    monkeypatch.setattr(Path, "open", tracking_open)

    result = hashing.calculate_file_hash(file_path, chunk_size=4)

    assert result == "72399361da6a7754fec986dca5b7cbaf1c810a28ded4abaf56b2106d06cb78b0"
    assert read_sizes == [4, 4, 4, 4]


def test_file_hashes_match_uses_safe_compare(tmp_path: Path, monkeypatch) -> None:
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"
    first_path.write_bytes(b"same")
    second_path.write_bytes(b"same")
    calls: list[tuple[str, str]] = []

    def fake_compare_digest(first: str, second: str) -> bool:
        calls.append((first, second))
        return first == second

    monkeypatch.setattr(hashing.hmac, "compare_digest", fake_compare_digest)

    assert hashing.file_hashes_match(first_path, second_path) is True
    assert len(calls) == 1


def test_image_hashes_match_distinguishes_different_content(tmp_path: Path) -> None:
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"
    first_path.write_bytes(b"first")
    second_path.write_bytes(b"second")

    assert hashing.image_hashes_match(first_path, second_path) is False


def test_calculate_image_hash_rejects_unsupported_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "photo.gif"
    file_path.write_bytes(b"image bytes")

    with pytest.raises(ValueError, match="Unsupported image file extension"):
        hashing.calculate_image_hash(file_path)


def test_calculate_file_hash_rejects_invalid_chunk_size(tmp_path: Path) -> None:
    file_path = tmp_path / "photo.jpg"
    file_path.write_bytes(b"image bytes")

    with pytest.raises(ValueError, match="chunk_size"):
        hashing.calculate_file_hash(file_path, chunk_size=0)
