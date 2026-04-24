import pytest
from pathlib import Path

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
    monkeypatch, capsys: pytest.CaptureFixture[str]
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

    result = main(["organize", "./photos", "--output", "./organized", "--plan"])

    assert result == 0
    captured = capsys.readouterr()
    assert "[INFO] Generated execution plan:" in captured.out
    assert "[PLAN] MOVE input/a.jpg -> out/2024/08/15/2024-08-15_14-32-09.jpg" in captured.out
    assert "Plan-only mode enabled" in captured.out
