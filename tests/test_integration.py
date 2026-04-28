from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from photo_organizer.cli import main


def _write_photo(path: Path, content: str, dt: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    timestamp = dt.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_organize_copy_pipeline_creates_directories_and_keeps_sources(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source = source_dir / "nested" / "IMG_1.jpg"
    photo_dt = datetime(2024, 8, 15, 14, 32, 9)
    expected_destination = (
        output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )

    _write_photo(source, "copy-data", photo_dt)

    result = main([
        "organize",
        str(source_dir),
        "--output",
        str(output_dir),
        "--copy",
    ])

    assert result == 0
    assert source.exists()
    assert source.read_text() == "copy-data"
    assert expected_destination.exists()
    assert expected_destination.read_text() == "copy-data"
    assert expected_destination.parent.is_dir()


def test_organize_move_pipeline_creates_directories_and_removes_sources(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source = source_dir / "IMG_2.png"
    photo_dt = datetime(2023, 1, 2, 3, 4, 5)
    expected_destination = (
        output_dir / "2023" / "01" / "02" / "2023-01-02_03-04-05.png"
    )

    _write_photo(source, "move-data", photo_dt)

    result = main([
        "organize",
        str(source_dir),
        "--output",
        str(output_dir),
        "--move",
    ])

    assert result == 0
    assert not source.exists()
    assert expected_destination.exists()
    assert expected_destination.read_text() == "move-data"
    assert expected_destination.parent.is_dir()


def test_organize_dry_run_pipeline_does_not_create_directories_or_move_files(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source = source_dir / "IMG_3.jpg"
    photo_dt = datetime(2022, 6, 7, 8, 9, 10)
    expected_destination = (
        output_dir / "2022" / "06" / "07" / "2022-06-07_08-09-10.jpg"
    )

    _write_photo(source, "dry-run-data", photo_dt)

    result = main([
        "organize",
        str(source_dir),
        "--output",
        str(output_dir),
        "--dry-run",
    ])

    assert result == 0
    assert source.exists()
    assert source.read_text() == "dry-run-data"
    assert not output_dir.exists()
    assert not expected_destination.exists()


def test_organize_pipeline_handles_destination_conflicts_without_overwriting(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    first_source = source_dir / "2025-10-31_11-07-10 (copy).png"
    second_source = source_dir / "2025-10-31_11-07-10.png"
    photo_dt = datetime(2025, 10, 31, 11, 7, 10)
    destination = output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10.png"
    suffixed_destination = (
        output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10_01.png"
    )

    _write_photo(first_source, "first", photo_dt)
    _write_photo(second_source, "second", photo_dt)
    destination.parent.mkdir(parents=True)
    destination.write_text("existing")

    result = main([
        "organize",
        str(source_dir),
        "--output",
        str(output_dir),
        "--copy",
    ])

    assert result == 0
    assert destination.read_text() == "existing"
    assert suffixed_destination.read_text() == "first"
    assert (
        output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10_02.png"
    ).read_text() == "second"
    assert first_source.exists()
    assert second_source.exists()
