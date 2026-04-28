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


def test_find_duplicate_images_returns_original_and_duplicates(tmp_path: Path) -> None:
    original = tmp_path / "a_original.jpg"
    duplicate = tmp_path / "b_duplicate.png"
    other = tmp_path / "c_other.jpg"
    original.write_bytes(b"same content")
    duplicate.write_bytes(b"same content")
    other.write_bytes(b"different content")

    groups = hashing.find_duplicate_images([other, duplicate, original])

    assert len(groups) == 1
    assert groups[0].original == original
    assert groups[0].duplicates == (duplicate,)


def test_find_duplicate_images_identifies_multiple_groups(tmp_path: Path) -> None:
    first_original = tmp_path / "a.jpg"
    first_duplicate = tmp_path / "b.jpg"
    second_original = tmp_path / "c.png"
    second_duplicate = tmp_path / "d.jpeg"
    first_original.write_bytes(b"group one")
    first_duplicate.write_bytes(b"group one")
    second_original.write_bytes(b"group two")
    second_duplicate.write_bytes(b"group two")

    groups = hashing.find_duplicate_images(
        [second_duplicate, first_duplicate, second_original, first_original]
    )

    assert [(group.original, group.duplicates) for group in groups] == [
        (first_original, (first_duplicate,)),
        (second_original, (second_duplicate,)),
    ]


def test_find_duplicate_images_has_no_false_positive_for_different_files(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"
    first_path.write_bytes(b"similar but not equal")
    second_path.write_bytes(b"similar but not equal.")

    groups = hashing.find_duplicate_images([first_path, second_path])

    assert groups == []


def test_find_duplicate_image_groups_scans_supported_images(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    original = tmp_path / "a.jpg"
    duplicate = nested / "b.jpg"
    unsupported = tmp_path / "c.gif"
    original.write_bytes(b"same")
    duplicate.write_bytes(b"same")
    unsupported.write_bytes(b"same")

    groups = hashing.find_duplicate_image_groups(tmp_path)

    assert len(groups) == 1
    assert groups[0].original == original
    assert groups[0].duplicates == (duplicate,)
