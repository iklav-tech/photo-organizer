from datetime import datetime
from pathlib import Path
import sys
import types

import photo_organizer.metadata as metadata


def test_extract_exif_metadata_reads_compatible_jpeg_exif(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    class FakeImage:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getexif(self):
            return {
                36867: "2024:01:02 03:04:05",
                306: "2024:01:02 03:04:05",
            }

    fake_image_module = types.SimpleNamespace(open=lambda _path: FakeImage())
    fake_exif_tags_module = types.SimpleNamespace(
        TAGS={36867: "DateTimeOriginal", 306: "DateTime"}
    )
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result["DateTimeOriginal"] == "2024:01:02 03:04:05"


def test_extract_exif_metadata_returns_empty_when_no_exif(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    class FakeImage:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getexif(self):
            return {}

    fake_image_module = types.SimpleNamespace(open=lambda _path: FakeImage())
    fake_exif_tags_module = types.SimpleNamespace(TAGS={})
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result == {}


def test_extract_exif_metadata_handles_read_exceptions_safely(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    def raise_open(_path):
        raise OSError("cannot read")

    fake_image_module = types.SimpleNamespace(open=raise_open)
    fake_exif_tags_module = types.SimpleNamespace(TAGS={})
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result == {}


def test_get_best_available_datetime_prioritizes_datetimeoriginal(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(
        metadata,
        "_read_exif_datetime_fields",
        lambda _path: {
            "DateTimeOriginal": "2024:01:02 03:04:05",
            "CreateDate": "2020:01:01 00:00:00",
        },
    )

    result = metadata.get_best_available_datetime(file_path)

    assert result == datetime(2024, 1, 2, 3, 4, 5)
    assert isinstance(result, datetime)


def test_get_best_available_datetime_uses_createdate_as_second_option(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(
        metadata,
        "_read_exif_datetime_fields",
        lambda _path: {
            "CreateDate": "2021:06:07 08:09:10",
        },
    )

    result = metadata.get_best_available_datetime(file_path)

    assert result == datetime(2021, 6, 7, 8, 9, 10)
    assert isinstance(result, datetime)


def test_get_best_available_datetime_falls_back_to_file_modification_time(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(metadata, "_read_exif_datetime_fields", lambda _path: {})

    expected_dt = datetime(2022, 9, 10, 11, 12, 13)
    timestamp = expected_dt.timestamp()
    file_path.touch()
    file_path.chmod(0o644)
    # Keep atime unchanged and force mtime to a deterministic timestamp.
    file_path.stat()
    import os

    os.utime(file_path, (timestamp, timestamp))

    result = metadata.get_best_available_datetime(file_path)

    assert result == datetime.fromtimestamp(timestamp)
    assert isinstance(result, datetime)
