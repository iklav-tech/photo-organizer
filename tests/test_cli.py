import pytest
from pathlib import Path
import logging

from photo_organizer.cli import main
from photo_organizer.executor import FileOperation


def test_root_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "scan" in captured.out
    assert "organize" in captured.out


def test_scan_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "source" in captured.out


def test_organize_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["organize", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "--output" in captured.out


def test_organize_requires_output(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["organize", "./photos"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "--output" in captured.err


def test_scan_requires_source(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "source" in captured.err


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


def test_log_level_can_be_adjusted(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [],
    )

    with caplog.at_level(logging.DEBUG):
        result = main(["--log-level", "ERROR", "scan", "./photos"])

    assert result == 0
    assert "Execution started: scan" not in caplog.text
