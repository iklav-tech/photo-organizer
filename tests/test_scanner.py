from pathlib import Path

import pytest

from photo_organizer.scanner import find_image_files


def test_find_image_files_supported_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.jpeg").write_text("x")
    (tmp_path / "c.png").write_text("x")
    (tmp_path / "d.tif").write_text("x")
    (tmp_path / "e.tiff").write_text("x")
    (tmp_path / "f.webp").write_text("x")
    (tmp_path / "g.bmp").write_text("x")
    (tmp_path / "h.heic").write_text("x")
    (tmp_path / "i.heif").write_text("x")
    (tmp_path / "j.hif").write_text("x")
    (tmp_path / "k.cr2").write_text("x")
    (tmp_path / "l.cr3").write_text("x")
    (tmp_path / "m.crw").write_text("x")
    (tmp_path / "n.nef").write_text("x")
    (tmp_path / "o.arw").write_text("x")
    (tmp_path / "p.rw2").write_text("x")
    (tmp_path / "q.orf").write_text("x")
    (tmp_path / "r.raf").write_text("x")

    result = find_image_files(tmp_path)

    assert result == [
        tmp_path / "a.jpg",
        tmp_path / "b.jpeg",
        tmp_path / "c.png",
        tmp_path / "d.tif",
        tmp_path / "e.tiff",
        tmp_path / "f.webp",
        tmp_path / "g.bmp",
        tmp_path / "h.heic",
        tmp_path / "i.heif",
        tmp_path / "j.hif",
        tmp_path / "k.cr2",
        tmp_path / "l.cr3",
        tmp_path / "m.crw",
        tmp_path / "n.nef",
        tmp_path / "o.arw",
        tmp_path / "p.rw2",
        tmp_path / "q.orf",
        tmp_path / "r.raf",
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
    (tmp_path / "bitmap.BMP").write_text("x")
    (tmp_path / "heic.HEIC").write_text("x")
    (tmp_path / "heif.HeIf").write_text("x")
    (tmp_path / "canon.CR3").write_text("x")
    (tmp_path / "nikon.NEF").write_text("x")
    (tmp_path / "sony.ArW").write_text("x")
    (tmp_path / "web.WEBP").write_text("x")
    (tmp_path / "ignored.GIF").write_text("x")

    result = find_image_files(tmp_path)

    assert result == [
        tmp_path / "bitmap.BMP",
        tmp_path / "canon.CR3",
        tmp_path / "heic.HEIC",
        tmp_path / "heif.HeIf",
        tmp_path / "lower.png",
        tmp_path / "mixed.JpEg",
        tmp_path / "nikon.NEF",
        tmp_path / "sony.ArW",
        tmp_path / "upper.JPG",
        tmp_path / "web.WEBP",
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
