from pathlib import Path

from PIL import Image

from photo_organizer.preview import (
    build_heic_preview_destination,
    generate_heic_preview,
    is_heif_image,
)


class FakeHeifBackend:
    def open(self, _path: str | Path):
        return Image.new("RGB", (1200, 800), color="red")


def test_is_heif_image_accepts_heic_extensions(tmp_path: Path) -> None:
    assert is_heif_image(tmp_path / "photo.heic") is True
    assert is_heif_image(tmp_path / "photo.HEIF") is True
    assert is_heif_image(tmp_path / "photo.jpg") is False


def test_build_heic_preview_destination_uses_hidden_preview_directory(
    tmp_path: Path,
) -> None:
    destination = build_heic_preview_destination(tmp_path / "organized" / "photo.heic")

    assert destination == tmp_path / "organized" / ".previews" / "photo.jpg"


def test_generate_heic_preview_writes_resized_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "photo.heic"
    source.write_bytes(b"fake-heic")
    destination = tmp_path / "previews" / "photo.jpg"

    result = generate_heic_preview(
        source,
        destination,
        max_size=256,
        backend=FakeHeifBackend(),
    )

    assert result == destination
    with Image.open(destination) as preview:
        assert preview.format == "JPEG"
        assert max(preview.size) == 256


def test_generate_heic_preview_skips_non_heif_images(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    destination = tmp_path / "previews" / "photo.jpg"

    result = generate_heic_preview(
        source,
        destination,
        backend=FakeHeifBackend(),
    )

    assert result is None
    assert not destination.exists()
