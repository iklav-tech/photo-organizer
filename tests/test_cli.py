import pytest
import csv
import hashlib
import json
from pathlib import Path
import logging
import os
from datetime import datetime

from photo_organizer.cli import main
from photo_organizer.executor import FileOperation


def test_root_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "scan" in captured.out
    assert "dedupe" in captured.out
    assert "organize" in captured.out
    assert "Examples:" in captured.out


def test_scan_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "SOURCE" in captured.out
    assert "Examples:" in captured.out


def test_dedupe_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["dedupe", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "SOURCE" in captured.out
    assert "--read-only" in captured.out
    assert "--report" in captured.out
    assert "Examples:" in captured.out


def test_organize_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["organize", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "--output" in captured.out
    assert "Paths:" in captured.out
    assert "Audit report:" in captured.out
    assert "Examples:" in captured.out


def test_organize_requires_output(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["organize", "./photos"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "organize requires --output DIR" in captured.err
    assert "photo-organizer organize ./Photos --output ./OrganizedPhotos" in captured.err


def test_scan_requires_source(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "SOURCE" in captured.err


def test_organize_rejects_unknown_report_extension(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([
            "organize",
            "./photos",
            "--output",
            "./organized",
            "--report",
            "audit.txt",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "organize --report must end with .json or .csv" in captured.err
    assert "--report audit.csv" in captured.err


def test_dedupe_rejects_unknown_report_extension(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["dedupe", "./photos", "--report", "duplicates.txt"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "dedupe --report must end with .json or .csv" in captured.err
    assert "--report duplicates.json" in captured.err


def test_organize_plan_mode_shows_plan_without_execution(
    monkeypatch, caplog
) -> None:
    planned = [
        FileOperation(
            source=Path("input/a.jpg"),
            destination=Path("out/2024/08/15/2024-08-15_14-32-09.jpg"),
            mode="move",
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("apply_operations must not be called in --plan mode")

    monkeypatch.setattr("photo_organizer.cli.apply_operations", fail_if_called)

    with caplog.at_level(logging.INFO):
        result = main(["organize", "./photos", "--output", "./organized", "--plan"])

    assert result == 0
    assert "Generated execution plan: operations=1" in caplog.text
    assert "Plan-only mode enabled" in caplog.text


def test_scan_logs_start_end_and_count(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [Path("a.jpg"), Path("b.jpg")],
    )

    with caplog.at_level(logging.INFO):
        result = main(["scan", "./photos"])

    assert result == 0
    assert "Execution started: scan source=./photos" in caplog.text
    assert "Execution finished: scan processed_files=2" in caplog.text


def test_scan_nonexistent_directory_returns_clear_message(caplog) -> None:
    with caplog.at_level(logging.INFO):
        result = main(["scan", "./does-not-exist"])

    assert result == 1
    assert "Source directory does not exist" in caplog.text
    assert "Execution finished: scan processed_files=0" in caplog.text


def test_dedupe_lists_duplicate_groups_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)
    original = source_dir / "a.jpg"
    duplicate = nested_dir / "b.png"
    different = source_dir / "c.jpg"
    original.write_bytes(b"same content")
    duplicate.write_bytes(b"same content")
    different.write_bytes(b"different content")

    result = main(["dedupe", str(source_dir), "--read-only"])

    assert result == 0
    captured = capsys.readouterr()
    assert "Duplicate group 1:" in captured.out
    assert "Hash:" in captured.out
    assert "Quantity: 2" in captured.out
    assert f"Original: {original}" in captured.out
    assert f"Duplicate: {duplicate}" in captured.out
    assert str(different) not in captured.out
    assert original.read_bytes() == b"same content"
    assert duplicate.read_bytes() == b"same content"
    assert different.read_bytes() == b"different content"


def test_dedupe_reports_no_duplicates_for_different_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    first = source_dir / "first.jpg"
    second = source_dir / "second.png"
    first.write_bytes(b"content one")
    second.write_bytes(b"content two")

    result = main(["dedupe", str(source_dir)])

    assert result == 0
    captured = capsys.readouterr()
    assert captured.out == "No duplicate images found.\n"


def test_dedupe_writes_structured_json_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    report_path = tmp_path / "reports" / "duplicates.json"
    source_dir.mkdir()
    original = source_dir / "a.jpg"
    duplicate = source_dir / "b.png"
    different = source_dir / "c.jpg"
    original.write_bytes(b"same content")
    duplicate.write_bytes(b"same content")
    different.write_bytes(b"different content")
    expected_hash = hashlib.sha256(b"same content").hexdigest()

    result = main(["dedupe", str(source_dir), "--report", str(report_path)])

    assert result == 0
    capsys.readouterr()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {
        "duplicate_groups": 1,
        "duplicate_files": 1,
        "total_files_in_duplicate_groups": 2,
    }
    assert report["duplicate_groups"] == [
        {
            "group_id": 1,
            "hash": expected_hash,
            "quantity": 2,
            "original": str(original),
            "duplicates": [str(duplicate)],
            "paths": [str(original), str(duplicate)],
        }
    ]


def test_dedupe_writes_analysis_friendly_csv_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    report_path = tmp_path / "duplicates.csv"
    source_dir.mkdir()
    original = source_dir / "a.jpg"
    duplicate = source_dir / "b.jpg"
    original.write_bytes(b"same content")
    duplicate.write_bytes(b"same content")
    expected_hash = hashlib.sha256(b"same content").hexdigest()

    result = main(["dedupe", str(source_dir), "--report", str(report_path)])

    assert result == 0
    capsys.readouterr()
    with report_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.DictReader(report_file))

    assert rows == [
        {
            "group_id": "1",
            "hash": expected_hash,
            "quantity": "2",
            "role": "original",
            "path": str(original),
        },
        {
            "group_id": "1",
            "hash": expected_hash,
            "quantity": "2",
            "role": "duplicate",
            "path": str(duplicate),
        },
    ]


def test_dedupe_nonexistent_directory_returns_clear_message(caplog) -> None:
    with caplog.at_level(logging.INFO):
        result = main(["dedupe", "./does-not-exist"])

    assert result == 1
    assert "Source directory does not exist" in caplog.text
    assert "Execution finished: dedupe duplicate_groups=0 duplicate_files=0" in caplog.text


def test_log_level_can_be_adjusted(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [],
    )

    with caplog.at_level(logging.DEBUG):
        result = main(["--log-level", "ERROR", "scan", "./photos"])

    assert result == 0
    assert "Execution started: scan" not in caplog.text


def test_organize_dry_run_end_to_end_shows_expected_destinations_and_keeps_files(
    tmp_path: Path, caplog
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source_dir.mkdir()

    first = source_dir / "IMG_1.jpg"
    second = source_dir / "IMG_2.png"
    ignored = source_dir / "notes.txt"
    first.write_text("a")
    second.write_text("b")
    ignored.write_text("ignore me")

    first_dt = (2024, 8, 15, 14, 32, 9)
    second_dt = (2023, 1, 2, 3, 4, 5)
    first_ts = datetime(*first_dt).timestamp()
    second_ts = datetime(*second_dt).timestamp()
    os.utime(first, (first_ts, first_ts))
    os.utime(second, (second_ts, second_ts))

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
            "--dry-run",
        ])

    assert result == 0

    first_expected = (
        output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )
    second_expected = (
        output_dir / "2023" / "01" / "02" / "2023-01-02_03-04-05.png"
    )

    assert f"[DRY-RUN] MOVE {first} -> {first_expected}" in caplog.text
    assert f"[DRY-RUN] MOVE {second} -> {second_expected}" in caplog.text

    # Dry-run must not alter input files or create output files.
    assert first.exists()
    assert second.exists()
    assert ignored.exists()
    assert not first_expected.exists()
    assert not second_expected.exists()
    assert (
        "Execution summary: mode=dry-run processed_files=2 ignored_files=1 "
        "error_files=0 fallback_files=2"
    ) in caplog.text


def test_organize_end_to_end_adds_suffixes_for_destination_collisions(
    tmp_path: Path, caplog
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source_dir.mkdir()

    first = source_dir / "2025-10-31_11-07-10 (Copia 2).png"
    second = source_dir / "2025-10-31_11-07-10 (Copia).png"
    third = source_dir / "2025-10-31_11-07-10.png"
    first.write_text("first")
    second.write_text("second")
    third.write_text("third")

    fallback_ts = datetime(2025, 10, 31, 11, 7, 10).timestamp()
    for source in [first, second, third]:
        os.utime(source, (fallback_ts, fallback_ts))

    expected_base = output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10.png"
    expected_first_suffix = (
        output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10_01.png"
    )
    expected_second_suffix = (
        output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10_02.png"
    )

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
        ])

    assert result == 0

    assert expected_base.read_text() == "first"
    assert expected_first_suffix.read_text() == "second"
    assert expected_second_suffix.read_text() == "third"
    assert not first.exists()
    assert not second.exists()
    assert not third.exists()

    assert f"MOVE {first} -> {expected_base}" in caplog.text
    assert f"MOVE {second} -> {expected_first_suffix}" in caplog.text
    assert f"MOVE {third} -> {expected_second_suffix}" in caplog.text
    assert (
        "Execution summary: mode=execute processed_files=3 ignored_files=0 "
        "error_files=0 fallback_files=3"
    ) in caplog.text


def test_organize_summary_counts_operation_errors(monkeypatch, caplog) -> None:
    planned = [
        FileOperation(
            source=Path("input/good.jpg"),
            destination=Path("out/good.jpg"),
            mode="copy",
            date_fallback=True,
        ),
        FileOperation(
            source=Path("input/bad.jpg"),
            destination=Path("out/bad.jpg"),
            mode="copy",
            date_fallback=False,
        ),
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/good.jpg -> out/good.jpg",
            "[ERROR] COPY input/bad.jpg -> out/bad.jpg (error: failed)",
        ],
    )

    with caplog.at_level(logging.INFO):
        result = main(["organize", "./photos", "--output", "./organized", "--copy"])

    assert result == 0
    assert (
        "Execution summary: mode=execute processed_files=1 ignored_files=0 "
        "error_files=1 fallback_files=1"
    ) in caplog.text


def test_organize_writes_valid_structured_execution_report(
    tmp_path: Path, caplog
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    report_path = tmp_path / "reports" / "execution.json"
    source_dir.mkdir()

    source = source_dir / "IMG_1.jpg"
    source.write_text("image-data")
    expected_ts = datetime(2024, 8, 15, 14, 32, 9).timestamp()
    os.utime(source, (expected_ts, expected_ts))

    destination = output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
            "--copy",
            "--report",
            str(report_path),
        ])

    assert result == 0
    assert "Execution report written" in caplog.text

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {
        "mode": "execute",
        "processed_files": 1,
        "ignored_files": 0,
        "error_files": 0,
        "fallback_files": 1,
    }
    assert report["operations"] == [
        {
            "source": str(source),
            "destination": str(destination),
            "action": "copy",
            "status": "success",
            "observations": "",
        }
    ]


def test_organize_report_includes_error_status_and_observation(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/bad.jpg"),
            destination=Path("out/bad.jpg"),
            mode="copy",
            date_fallback=False,
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[ERROR] COPY input/bad.jpg -> out/bad.jpg (error: permission denied)",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["error_files"] == 1
    assert report["operations"] == [
        {
            "source": "input/bad.jpg",
            "destination": "out/bad.jpg",
            "action": "copy",
            "status": "error",
            "observations": "permission denied",
        }
    ]


def test_organize_writes_valid_csv_execution_report(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "reports" / "execution.csv"
    planned = [
        FileOperation(
            source=Path("input/good.jpg"),
            destination=Path("out/good.jpg"),
            mode="copy",
            date_fallback=False,
        ),
        FileOperation(
            source=Path("input/bad.jpg"),
            destination=Path("out/bad.jpg"),
            mode="copy",
            date_fallback=False,
        ),
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/good.jpg -> out/good.jpg",
            "[ERROR] COPY input/bad.jpg -> out/bad.jpg (error: permission denied)",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    with report_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.DictReader(report_file))

    assert rows == [
        {
            "source": "input/good.jpg",
            "destination": "out/good.jpg",
            "action": "copy",
            "status": "success",
            "observations": "",
        },
        {
            "source": "input/bad.jpg",
            "destination": "out/bad.jpg",
            "action": "copy",
            "status": "error",
            "observations": "permission denied",
        },
    ]
