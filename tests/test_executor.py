from pathlib import Path
from datetime import datetime
import logging
import os

from photo_organizer.executor import FileOperation, apply_operations, plan_organization_operations
from photo_organizer.metadata import DateTimeResolution


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
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
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

    def raise_copy(_src, _dst):
        raise OSError("permission denied")

    monkeypatch.setattr("photo_organizer.executor.shutil.copy2", raise_copy)

    with caplog.at_level(logging.ERROR):
        logs = apply_operations(
            [FileOperation(source=source, destination=destination, mode="move")],
            dry_run=False,
        )

    assert "Failed to execute operation: action=MOVE" in caplog.text
    assert str(source) in caplog.text
    assert str(destination) in caplog.text
    assert logs[0].startswith("[ERROR] MOVE")
    assert source.exists()
    assert not destination.exists()


def test_apply_operations_move_removes_source_after_success(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    expected_mtime = datetime(2024, 2, 3, 4, 5, 6).timestamp()
    os.utime(source, (expected_mtime, expected_mtime))

    destination = tmp_path / "out" / "source.jpg"
    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=False,
    )

    assert not source.exists()
    assert destination.exists()
    assert destination.read_text() == "image-data"
    assert destination.stat().st_mtime == expected_mtime
    assert logs == [f"[INFO] MOVE {source} -> {destination}"]


def test_apply_operations_move_creates_missing_destination_directories(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "source.jpg"

    assert not destination.parent.exists()

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=False,
    )

    assert destination.parent.is_dir()
    assert destination.exists()
    assert not source.exists()
    assert logs == [f"[INFO] MOVE {source} -> {destination}"]


def test_apply_operations_copy_creates_missing_destination_directories(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "source.jpg"

    assert not destination.parent.exists()

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.parent.is_dir()
    assert destination.exists()
    assert source.exists()
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_is_idempotent_when_destination_directory_exists(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "source.jpg"
    destination.parent.mkdir(parents=True)

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.parent.is_dir()
    assert destination.exists()
    assert source.exists()
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_move_keeps_source_when_removal_fails(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "source.jpg"

    original_unlink = Path.unlink

    def raise_for_source(path: Path, *args, **kwargs):
        if path == source:
            raise OSError("cannot remove source")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", raise_for_source)

    with caplog.at_level(logging.ERROR):
        logs = apply_operations(
            [FileOperation(source=source, destination=destination, mode="move")],
            dry_run=False,
        )

    assert source.exists()
    assert not destination.exists()
    assert "cannot remove source" in caplog.text
    assert logs[0].startswith(f"[ERROR] MOVE {source} -> {destination}")


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


def test_apply_operations_copy_uses_suffix_when_destination_exists(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")

    suffixed_destination = tmp_path / "out" / "source_01.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-data"
    assert suffixed_destination.read_text() == "new-data"
    assert source.exists()
    assert logs == [f"[INFO] COPY {source} -> {suffixed_destination}"]


def test_apply_operations_move_uses_suffix_when_destination_exists(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")

    suffixed_destination = tmp_path / "out" / "source_01.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-data"
    assert suffixed_destination.read_text() == "new-data"
    assert not source.exists()
    assert logs == [f"[INFO] MOVE {source} -> {suffixed_destination}"]


def test_apply_operations_uses_next_available_suffix_predictably(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    first_collision = tmp_path / "out" / "source_01.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")
    first_collision.write_text("also-existing")

    second_suffix = tmp_path / "out" / "source_02.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-data"
    assert first_collision.read_text() == "also-existing"
    assert second_suffix.read_text() == "new-data"
    assert logs == [f"[INFO] COPY {source} -> {second_suffix}"]


def test_apply_operations_uses_third_suffix_without_overwriting_existing_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    first_collision = tmp_path / "out" / "source_01.jpg"
    second_collision = tmp_path / "out" / "source_02.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-base")
    first_collision.write_text("existing-01")
    second_collision.write_text("existing-02")

    third_suffix = tmp_path / "out" / "source_03.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-base"
    assert first_collision.read_text() == "existing-01"
    assert second_collision.read_text() == "existing-02"
    assert third_suffix.read_text() == "new-data"
    assert logs == [f"[INFO] COPY {source} -> {third_suffix}"]


def test_apply_operations_dry_run_reserves_destinations_for_same_batch(
    tmp_path: Path,
) -> None:
    first_source = tmp_path / "first.jpg"
    second_source = tmp_path / "second.jpg"
    first_source.write_text("first")
    second_source.write_text("second")
    destination = tmp_path / "out" / "same.jpg"
    suffixed_destination = tmp_path / "out" / "same_01.jpg"

    logs = apply_operations(
        [
            FileOperation(source=first_source, destination=destination, mode="copy"),
            FileOperation(source=second_source, destination=destination, mode="copy"),
        ],
        dry_run=True,
    )

    assert logs == [
        f"[DRY-RUN] COPY {first_source} -> {destination}",
        f"[DRY-RUN] COPY {second_source} -> {suffixed_destination}",
    ]
    assert not destination.exists()
    assert not suffixed_destination.exists()


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
