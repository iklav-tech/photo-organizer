from pathlib import Path
from datetime import datetime
import logging
import os

from photo_organizer.executor import FileOperation, apply_operations, plan_organization_operations


def test_apply_operations_dry_run_move_does_not_modify_files(tmp_path: Path) -> None:
    source = tmp_path / "input.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "input.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=True,
    )

    assert source.exists()
    assert not destination.exists()
    assert logs == [f"[DRY-RUN] MOVE {source} -> {destination}"]


def test_apply_operations_dry_run_copy_does_not_modify_files(tmp_path: Path) -> None:
    source = tmp_path / "input.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "input.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=True,
    )

    assert source.exists()
    assert not destination.exists()
    assert logs == [f"[DRY-RUN] COPY {source} -> {destination}"]


def test_apply_operations_real_and_dry_run_share_same_planned_behavior(
    tmp_path: Path,
) -> None:
    source_dry = tmp_path / "dry.jpg"
    source_dry.write_text("image-data")
    source_real = tmp_path / "real.jpg"
    source_real.write_text("image-data")

    destination_dry = tmp_path / "out" / "2020" / "01" / "02" / "dry.jpg"
    destination_real = tmp_path / "out" / "2020" / "01" / "02" / "real.jpg"

    dry_logs = apply_operations(
        [FileOperation(source=source_dry, destination=destination_dry, mode="move")],
        dry_run=True,
    )
    real_logs = apply_operations(
        [FileOperation(source=source_real, destination=destination_real, mode="move")],
        dry_run=False,
    )

    dry_suffix = dry_logs[0].split("] ", maxsplit=1)[1].replace(str(source_dry), "<SRC>").replace(
        str(destination_dry), "<DST>"
    )
    real_suffix = real_logs[0].split("] ", maxsplit=1)[1].replace(
        str(source_real), "<SRC>"
    ).replace(str(destination_real), "<DST>")

    assert dry_suffix == real_suffix
    assert source_dry.exists()
    assert not destination_dry.exists()
    assert not source_real.exists()
    assert destination_real.exists()


def test_plan_organization_operations_builds_operations_for_found_images(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"

    first_image = source_dir / "a.jpg"
    second_image = source_dir / "b.jpeg"
    first_image.write_text("a")
    second_image.write_text("b")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [first_image, second_image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.get_best_available_datetime",
        lambda _p: datetime(2024, 8, 15, 14, 32, 9),
    )

    operations = plan_organization_operations(source_dir, output_dir, mode="move")

    assert len(operations) == 2
    assert operations[0].source == first_image
    assert operations[0].destination == output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    assert operations[0].mode == "move"


def test_apply_operations_logs_errors_with_context(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    source = tmp_path / "input.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "input.jpg"

    def raise_move(_src, _dst):
        raise OSError("permission denied")

    monkeypatch.setattr("photo_organizer.executor.shutil.move", raise_move)

    with caplog.at_level(logging.ERROR):
        logs = apply_operations(
            [FileOperation(source=source, destination=destination, mode="move")],
            dry_run=False,
        )

    assert "Failed to execute operation: action=MOVE" in caplog.text
    assert str(source) in caplog.text
    assert str(destination) in caplog.text
    assert logs[0].startswith("[ERROR] MOVE")


def test_apply_operations_copy_preserves_basic_metadata_when_possible(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    expected_mtime = datetime(2024, 2, 3, 4, 5, 6).timestamp()
    os.utime(source, (expected_mtime, expected_mtime))

    destination = tmp_path / "out" / "source.jpg"
    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert source.exists()
    assert destination.exists()
    assert destination.read_text() == "image-data"
    assert destination.stat().st_mtime == source.stat().st_mtime
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_reports_success_and_failure_per_item(tmp_path: Path) -> None:
    good_source = tmp_path / "good.jpg"
    good_source.write_text("ok")
    bad_source = tmp_path / "missing.jpg"

    good_destination = tmp_path / "out" / "good.jpg"
    bad_destination = tmp_path / "out" / "missing.jpg"

    logs = apply_operations(
        [
            FileOperation(source=good_source, destination=good_destination, mode="copy"),
            FileOperation(source=bad_source, destination=bad_destination, mode="copy"),
        ],
        dry_run=False,
    )

    assert good_destination.exists()
    assert len(logs) == 2
    assert logs[0] == f"[INFO] COPY {good_source} -> {good_destination}"
    assert logs[1].startswith(f"[ERROR] COPY {bad_source} -> {bad_destination}")
