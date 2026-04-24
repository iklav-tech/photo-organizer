"""Execution logic for organizing photo files."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import shutil

from photo_organizer.metadata import get_best_available_datetime
from photo_organizer.naming import build_default_filename
from photo_organizer.planner import build_date_destination
from photo_organizer.scanner import find_image_files


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileOperation:
    """A planned file operation from source to destination."""

    source: Path
    destination: Path
    mode: str


def plan_organization_operations(
    source_dir: str | Path,
    output_dir: str | Path,
    mode: str = "move",
) -> list[FileOperation]:
    """Plan organization operations for all supported images in source_dir."""
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    logger.debug(
        "Planning operations: source=%s output=%s mode=%s",
        source_path,
        output_path,
        mode,
    )

    operations: list[FileOperation] = []
    for image_path in find_image_files(source_path, recursive=True):
        dt = get_best_available_datetime(image_path)
        destination_dir = Path(build_date_destination(output_path, dt))
        destination_file = destination_dir / build_default_filename(dt, image_path)
        operations.append(
            FileOperation(source=image_path, destination=destination_file, mode=mode)
        )

    return operations


def apply_operations(
    operations: list[FileOperation],
    dry_run: bool = False,
) -> list[str]:
    """Apply planned operations or simulate them when dry_run is True.

    Returns one status line per operation, including failures, so callers can
    inspect per-item outcomes.
    """
    logs: list[str] = []

    for operation in operations:
        action = operation.mode.upper()
        line_suffix = f"{action} {operation.source} -> {operation.destination}"

        if dry_run:
            logs.append(f"[DRY-RUN] {line_suffix}")
            continue

        try:
            operation.destination.parent.mkdir(parents=True, exist_ok=True)

            if operation.mode == "copy":
                shutil.copy2(operation.source, operation.destination)
            else:
                shutil.move(str(operation.source), str(operation.destination))
        except Exception as exc:
            logger.error(
                "Failed to execute operation: action=%s source=%s destination=%s error=%s",
                action,
                operation.source,
                operation.destination,
                exc,
            )
            logs.append(f"[ERROR] {line_suffix} (error: {exc})")
            continue

        logs.append(f"[INFO] {line_suffix}")

    return logs
