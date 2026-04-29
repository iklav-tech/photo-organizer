"""Execution logic for organizing photo files."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import shutil

from photo_organizer.geocoding import (
    ReverseGeocodedLocation,
    reverse_geocode_coordinates,
)
from photo_organizer.metadata import (
    extract_gps_coordinates,
    resolve_best_available_datetime,
)
from photo_organizer.naming import build_default_filename
from photo_organizer.planner import build_date_destination
from photo_organizer.scanner import find_image_files


logger = logging.getLogger(__name__)


def _resolve_available_destination(destination: Path, reserved: set[Path]) -> Path:
    """Return a destination path that does not overwrite existing or reserved files."""
    if not destination.exists() and destination not in reserved:
        return destination

    counter = 1
    while True:
        candidate = destination.with_name(
            f"{destination.stem}_{counter:02d}{destination.suffix}"
        )
        if not candidate.exists() and candidate not in reserved:
            return candidate
        counter += 1


def _move_file_after_successful_copy(source: Path, destination: Path) -> None:
    """Move a file by copying first and removing the source only after success."""
    shutil.copy2(source, destination)
    if not destination.exists():
        raise FileNotFoundError(f"Destination was not created: {destination}")

    try:
        source.unlink()
    except Exception:
        try:
            destination.unlink(missing_ok=True)
        except OSError as cleanup_exc:
            logger.warning(
                "Failed to clean up copied destination after source removal failure: "
                "source=%s destination=%s error=%s",
                source,
                destination,
                cleanup_exc,
            )
        raise


@dataclass(frozen=True)
class FileOperation:
    """A planned file operation from source to destination."""

    source: Path
    destination: Path
    mode: str
    date_fallback: bool = False
    location: ReverseGeocodedLocation | None = None
    location_status: str = "disabled"


def plan_organization_operations(
    source_dir: str | Path,
    output_dir: str | Path,
    mode: str = "move",
    reverse_geocode: bool = False,
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
        try:
            resolved_dt = resolve_best_available_datetime(image_path)
        except Exception as exc:
            logger.error(
                "Failed to plan file operation: source=%s error=%s",
                image_path,
                exc,
            )
            continue

        dt = resolved_dt.value
        location = None
        location_status = "disabled"
        if reverse_geocode:
            location_status = "missing-gps"
            try:
                coordinates = extract_gps_coordinates(image_path)
                if coordinates is not None:
                    location_status = "unresolved"
                    location = reverse_geocode_coordinates(coordinates)
                if location is not None:
                    location_status = "resolved"
                    logger.info(
                        "Location resolved from GPS: source=%s city=%s state=%s country=%s",
                        image_path,
                        location.city,
                        location.state,
                        location.country,
                    )
            except Exception as exc:
                location_status = "error"
                logger.warning(
                    "Reverse geocoding skipped after metadata error: source=%s error=%s",
                    image_path,
                    exc,
                )

        destination_dir = Path(build_date_destination(output_path, dt))
        destination_file = destination_dir / build_default_filename(dt, image_path)
        operations.append(
            FileOperation(
                source=image_path,
                destination=destination_file,
                mode=mode,
                date_fallback=resolved_dt.used_fallback,
                location=location,
                location_status=location_status,
            )
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
    reserved_destinations: set[Path] = set()

    for operation in operations:
        action = operation.mode.upper()
        destination = _resolve_available_destination(
            operation.destination,
            reserved_destinations,
        )
        reserved_destinations.add(destination)
        line_suffix = f"{action} {operation.source} -> {destination}"

        if dry_run:
            logs.append(f"[DRY-RUN] {line_suffix}")
            continue

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)

            if operation.mode == "copy":
                shutil.copy2(operation.source, destination)
            else:
                _move_file_after_successful_copy(
                    operation.source,
                    destination,
                )
        except Exception as exc:
            logger.error(
                "Failed to execute operation: action=%s source=%s destination=%s error=%s",
                action,
                operation.source,
                destination,
                exc,
            )
            logs.append(f"[ERROR] {line_suffix} (error: {exc})")
            continue

        logs.append(f"[INFO] {line_suffix}")

    return logs
