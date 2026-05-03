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
    GPSCoordinates,
    MetadataProvenance,
    ReconciliationDecision,
    ReconciliationPolicy,
    extract_iptc_iim_location,
    extract_gps_coordinates,
    resolve_best_available_datetime,
    validate_reconciliation_policy,
)
from photo_organizer.naming import (
    build_default_filename,
    build_pattern_filename,
    describe_pattern_filename_normalization,
)
from photo_organizer.planner import (
    build_city_state_month_destination,
    build_date_destination,
    build_location_date_destination,
    build_location_destination,
    build_pattern_destination,
    describe_location_part_normalization,
)
from photo_organizer.scanner import find_image_files
from photo_organizer.text_normalization import normalize_text


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
    date_provenance: MetadataProvenance | None = None
    date_reconciliation: ReconciliationDecision | None = None
    date_kind: str = "captured"
    coordinates: GPSCoordinates | None = None
    location: ReverseGeocodedLocation | None = None
    location_provenance: MetadataProvenance | None = None
    location_status: str = "disabled"
    organization_fallback: bool = False
    text_normalization_observations: tuple[str, ...] = ()


def plan_organization_operations(
    source_dir: str | Path,
    output_dir: str | Path,
    mode: str = "move",
    reverse_geocode: bool = False,
    organization_strategy: str = "date",
    naming_pattern: str | None = None,
    destination_pattern: str | None = None,
    reconciliation_policy: ReconciliationPolicy = "precedence",
    date_heuristics: bool = True,
) -> list[FileOperation]:
    """Plan organization operations for all supported images in source_dir."""
    reconciliation_policy = validate_reconciliation_policy(reconciliation_policy)
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
            try:
                resolved_dt = resolve_best_available_datetime(
                    image_path,
                    reconciliation_policy=reconciliation_policy,
                    date_heuristics=date_heuristics,
                )
            except TypeError:
                resolved_dt = resolve_best_available_datetime(image_path)
        except Exception as exc:
            logger.error(
                "Failed to plan file operation: source=%s error=%s",
                image_path,
                exc,
            )
            continue

        dt = resolved_dt.value
        coordinates = None
        location = None
        location_provenance = None
        location_status = "disabled"
        should_reverse_geocode = reverse_geocode or organization_strategy in {
            "city-state-month",
            "location",
            "location-date",
        }
        if should_reverse_geocode:
            location_status = "missing-gps"
            try:
                coordinates = extract_gps_coordinates(image_path)
                if coordinates is not None:
                    location_status = "unresolved"
                    location = reverse_geocode_coordinates(coordinates)
                if location is not None:
                    location_status = "resolved"
                    location_provenance = MetadataProvenance(
                        source="Reverse geocoding",
                        field="GPSLatitudeDecimal,GPSLongitudeDecimal",
                        confidence="medium",
                        raw_value={
                            "latitude": coordinates.latitude,
                            "longitude": coordinates.longitude,
                        },
                    )
                    logger.info(
                        "Location resolved: source=%s city=%s state=%s country=%s provenance=%s confidence=%s",
                        image_path,
                        location.city,
                        location.state,
                        location.country,
                        location_provenance.label,
                        location_provenance.confidence,
                    )
                if location is None:
                    iptc_location = extract_iptc_iim_location(image_path)
                    if iptc_location is not None:
                        location_fields, location_provenance = iptc_location
                        location = ReverseGeocodedLocation(
                            city=location_fields.get("city"),
                            state=location_fields.get("state"),
                            country=location_fields.get("country"),
                        )
                        location_status = "resolved"
                        logger.info(
                            "Location resolved: source=%s city=%s state=%s country=%s provenance=%s confidence=%s",
                            image_path,
                            location.city,
                            location.state,
                            location.country,
                            location_provenance.label,
                            location_provenance.confidence,
                        )
            except Exception as exc:
                location_status = "error"
                logger.warning(
                    "Reverse geocoding skipped after metadata error: source=%s error=%s",
                    image_path,
                    exc,
                )

        organization_fallback = False
        text_normalization_observations: list[str] = []
        if location is not None:
            for field_name, value in (
                ("city", location.city),
                ("state", location.state),
                ("country", location.country),
            ):
                observation = describe_location_part_normalization(field_name, value)
                if observation is not None:
                    text_normalization_observations.append(observation)
            location = ReverseGeocodedLocation(
                city=normalize_text(location.city).value
                if location.city is not None
                else None,
                state=normalize_text(location.state).value
                if location.state is not None
                else None,
                country=normalize_text(location.country).value
                if location.country is not None
                else None,
            )
        try:
            if destination_pattern is not None:
                destination_dir = Path(
                    build_pattern_destination(
                        output_path,
                        dt,
                        destination_pattern,
                        location,
                    )
                )
                organization_fallback = (
                    organization_strategy in {
                        "city-state-month",
                        "location",
                        "location-date",
                    }
                    and location is None
                )
            elif organization_strategy == "location" and location is not None:
                destination_dir = Path(build_location_destination(output_path, location))
            elif organization_strategy == "location-date" and location is not None:
                destination_dir = Path(
                    build_location_date_destination(output_path, location, dt)
                )
            elif organization_strategy == "city-state-month" and location is not None:
                destination_dir = Path(
                    build_city_state_month_destination(output_path, location, dt)
                )
            else:
                organization_fallback = organization_strategy in {
                    "city-state-month",
                    "location",
                    "location-date",
                }
                destination_dir = Path(build_date_destination(output_path, dt))
            filename = (
                build_pattern_filename(dt, image_path, naming_pattern)
                if naming_pattern is not None
                else build_default_filename(dt, image_path)
            )
            if naming_pattern is not None:
                observation = describe_pattern_filename_normalization(
                    dt,
                    image_path,
                    naming_pattern,
                )
                if observation is not None:
                    text_normalization_observations.append(observation)
        except Exception as exc:
            logger.error(
                "Failed to plan file operation: source=%s error=%s",
                image_path,
                exc,
            )
            continue

        destination_file = destination_dir / filename
        operations.append(
            FileOperation(
                source=image_path,
                destination=destination_file,
                mode=mode,
                date_fallback=resolved_dt.used_fallback,
                date_provenance=resolved_dt.provenance,
                date_reconciliation=resolved_dt.reconciliation,
                date_kind=resolved_dt.date_kind,
                coordinates=coordinates,
                location=location,
                location_provenance=location_provenance,
                location_status=location_status,
                organization_fallback=organization_fallback,
                text_normalization_observations=tuple(text_normalization_observations),
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
