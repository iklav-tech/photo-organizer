from pathlib import Path

import pytest

from photo_organizer.scanner import find_image_files


def test_find_image_files_supported_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.jpeg").write_text("x")
    (tmp_path / "c.png").write_text("x")

    result = find_image_files(tmp_path)

    assert result == [
        tmp_path / "a.jpg",
        tmp_path / "b.jpeg",
        tmp_path / "c.png",
    ]


def test_find_image_files_recursive_search(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "deep"
    nested.mkdir(parents=True)
    image_file = nested / "photo.jpg"
    image_file.write_text("x")

    result = find_image_files(tmp_path, recursive=True)

    assert result == [image_file]


def test_find_image_files_ignores_unsupported(tmp_path: Path) -> None:
    (tmp_path / "ok.jpg").write_text("x")
    (tmp_path / "skip.gif").write_text("x")
    (tmp_path / "skip.txt").write_text("x")

    result = find_image_files(tmp_path)

    assert result == [tmp_path / "ok.jpg"]


def test_find_image_files_is_case_insensitive_for_extensions(tmp_path: Path) -> None:
    (tmp_path / "upper.JPG").write_text("x")
    (tmp_path / "mixed.JpEg").write_text("x")
    (tmp_path / "lower.png").write_text("x")
    (tmp_path / "ignored.BMP").write_text("x")

    result = find_image_files(tmp_path)

    assert result == [
        tmp_path / "lower.png",
        tmp_path / "mixed.JpEg",
        tmp_path / "upper.JPG",
    ]


def test_find_image_files_returns_stable_sorted_paths(tmp_path: Path) -> None:
    (tmp_path / "z.jpg").write_text("x")
    (tmp_path / "m.png").write_text("x")
    (tmp_path / "a.jpeg").write_text("x")

    result = find_image_files(tmp_path)

    assert result == [
        tmp_path / "a.jpeg",
        tmp_path / "m.png",
        tmp_path / "z.jpg",
    ]


def test_find_image_files_raises_for_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_image_files(tmp_path / "missing")
