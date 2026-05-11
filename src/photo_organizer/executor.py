"""Execution logic for organizing photo files."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import shutil

from photo_organizer.correction_manifest import (
    CorrectionApplication,
    CorrectionManifest,
    CorrectionPriority,
    correction_for_file,
)
from photo_organizer.constants import RAW_IMAGE_FILE_EXTENSIONS
from photo_organizer.geocoding import (
    ReverseGeocodedLocation,
    reverse_geocode_coordinates,
)
from photo_organizer.metadata import (
    GPSCoordinates,
    MetadataProvenance,
    ReconciliationDecision,
    ReconciliationPolicy,
    extract_camera_profile,
    extract_gps_coordinates,
    infer_textual_location,
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
from photo_organizer.preview import build_heic_preview_destination, generate_heic_preview
from photo_organizer.scanner import find_image_files
from photo_organizer.text_normalization import normalize_text


logger = logging.getLogger(__name__)

SIDECAR_EXTENSIONS = frozenset({".xmp"})


def find_related_sidecars(path: str | Path) -> tuple[Path, ...]:
    """Return same-basename sidecars that should follow a RAW file."""
    raw_path = Path(path)
    if raw_path.suffix.lower() not in RAW_IMAGE_FILE_EXTENSIONS:
        return ()
    if not raw_path.parent.is_dir():
        return ()

    sidecars: list[Path] = []
    try:
        siblings = list(raw_path.parent.iterdir())
    except OSError as exc:
        logger.warning("Failed to inspect RAW sidecars: source=%s error=%s", raw_path, exc)
        return ()

    for candidate in siblings:
        if (
            candidate.is_file()
            and candidate.stem == raw_path.stem
            and candidate.suffix.lower() in SIDECAR_EXTENSIONS
        ):
            sidecars.append(candidate)
    return tuple(sorted(sidecars, key=lambda item: str(item)))


def _sidecar_destination(primary_destination: Path, sidecar: Path) -> Path:
    return primary_destination.with_suffix(sidecar.suffix)


def _resolve_available_operation_destination(
    destination: Path,
    related_sidecars: tuple[Path, ...],
    reserved: set[Path],
) -> Path:
    """Return a destination that also leaves room for linked sidecars."""
    counter = 0
    while True:
        candidate = (
            destination
            if counter == 0
            else destination.with_name(
                f"{destination.stem}_{counter:02d}{destination.suffix}"
            )
        )
        linked_destinations = {
            _sidecar_destination(candidate, sidecar)
            for sidecar in related_sidecars
        }
        if (
            not candidate.exists()
            and candidate not in reserved
            and all(
                not sidecar_destination.exists()
                and sidecar_destination not in reserved
                for sidecar_destination in linked_destinations
            )
        ):
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
    location_kind: str = "none"
    location_status: str = "disabled"
    organization_fallback: bool = False
    text_normalization_observations: tuple[str, ...] = ()
    correction_manifest: CorrectionApplication | None = None
    related_sidecars: tuple[Path, ...] = ()


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
    location_inference: bool = True,
    correction_manifest: CorrectionManifest | None = None,
    correction_priority: CorrectionPriority | None = None,
    clock_offset: str | None = None,
) -> list[FileOperation]:
    """Plan organization operations for all supported images in source_dir.

    When *clock_offset* is provided it is applied as a global time correction to
    every file that does not already have a per-file ``clock_offset`` set in the
    *correction_manifest*.  The offset is merged into the per-file
    :class:`~photo_organizer.correction_manifest.CorrectionApplication` so the
    original datetime is always preserved in the provenance ``raw_value``.

    Accepted offset formats: ``+3h``, ``-1d``, ``+00:30``, ``-5:45``, ``+12``.
    """
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
        camera_profile = (
            extract_camera_profile(image_path)
            if correction_manifest is not None
            else None
        )
        correction = correction_for_file(
            correction_manifest,
            image_path,
            source_path,
            correction_priority,
            camera_profile,
        )
        # Apply the global clock_offset when the per-file correction does not
        # already carry one.  We synthesise a minimal CorrectionApplication so
        # the offset flows through the same metadata resolution path and the
        # original datetime is preserved in the provenance raw_value.
        if clock_offset is not None:
            if correction is None:
                correction = CorrectionApplication(
                    source_path=source_path,
                    selectors=("global:clock_offset",),
                    clock_offset=clock_offset,
                    priority=correction_priority or "highest",
                )
            elif correction.clock_offset is None:
                correction = CorrectionApplication(
                    source_path=correction.source_path,
                    selectors=correction.selectors,
                    date_value=correction.date_value,
                    timezone=correction.timezone,
                    clock_offset=clock_offset,
                    city=correction.city,
                    state=correction.state,
                    country=correction.country,
                    event_name=correction.event_name,
                    priority=correction.priority,
                )
        try:
            try:
                resolved_dt = resolve_best_available_datetime(
                    image_path,
                    reconciliation_policy=reconciliation_policy,
                    date_heuristics=date_heuristics,
                    correction=correction,
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
        location_kind = "none"
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
                    location_kind = "gps"
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
                if location is None and location_inference:
                    inferred_location = None
                    if correction is not None and correction.location is not None:
                        inferred_location = (
                            correction.location,
                            MetadataProvenance(
                                source="Correction manifest",
                                field=",".join(correction.selectors),
                                confidence="high",
                                raw_value={
                                    "manifest": str(correction.source_path),
                                    "location": correction.location,
                                },
                            ),
                        )
                    if inferred_location is None:
                        inferred_location = infer_textual_location(image_path)
                    if inferred_location is not None:
                        location_fields, location_provenance = inferred_location
                        location = ReverseGeocodedLocation(
                            city=location_fields.get("city"),
                            state=location_fields.get("state"),
                            country=location_fields.get("country"),
                        )
                        location_status = "inferred"
                        location_kind = "inferred"
                        logger.info(
                            "Location inferred: source=%s city=%s state=%s country=%s provenance=%s confidence=%s",
                            image_path,
                            location.city,
                            location.state,
                            location.country,
                            location_provenance.label,
                            location_provenance.confidence,
                        )
                if (
                    location is None
                    and not location_inference
                    and organization_strategy in {
                        "city-state-month",
                        "location",
                        "location-date",
                    }
                ):
                    location = ReverseGeocodedLocation(
                        city="UnknownLocation",
                        state="UnknownLocation",
                        country="UnknownLocation",
                    )
                    location_status = "unknown-location"
                    location_kind = "unknown"
                    location_provenance = MetadataProvenance(
                        source="User policy",
                        field="UnknownLocation",
                        confidence="low",
                        raw_value="location inference disabled",
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
                if location_status == "unknown-location":
                    destination_dir = output_path / "UnknownLocation" / dt.strftime("%Y-%m")
                else:
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
        related_sidecars = find_related_sidecars(image_path)
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
                location_kind=location_kind,
                location_status=location_status,
                organization_fallback=organization_fallback,
                text_normalization_observations=tuple(text_normalization_observations),
                correction_manifest=correction,
                related_sidecars=related_sidecars,
            )
        )

    return operations


def apply_operations(
    operations: list[FileOperation],
    dry_run: bool = False,
    heic_preview: bool = False,
) -> list[str]:
    """Apply planned operations or simulate them when dry_run is True.

    Returns one status line per operation, including failures, so callers can
    inspect per-item outcomes.
    """
    logs: list[str] = []
    reserved_destinations: set[Path] = set()

    for operation in operations:
        action = operation.mode.upper()
        destination = _resolve_available_operation_destination(
            operation.destination,
            operation.related_sidecars,
            reserved_destinations,
        )
        reserved_destinations.add(destination)
        for sidecar in operation.related_sidecars:
            reserved_destinations.add(_sidecar_destination(destination, sidecar))
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
            for sidecar in operation.related_sidecars:
                sidecar_destination = _sidecar_destination(destination, sidecar)
                if operation.mode == "copy":
                    shutil.copy2(sidecar, sidecar_destination)
                else:
                    _move_file_after_successful_copy(sidecar, sidecar_destination)
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

        if heic_preview:
            preview_destination = build_heic_preview_destination(destination)
            try:
                preview_path = generate_heic_preview(
                    destination,
                    preview_destination,
                )
                if preview_path is not None:
                    logger.info(
                        "HEIC preview generated: source=%s preview=%s",
                        destination,
                        preview_path,
                    )
            except Exception as exc:
                logger.warning(
                    "HEIC preview generation failed: source=%s preview=%s error=%s",
                    destination,
                    preview_destination,
                    exc,
                )

        logs.append(f"[INFO] {line_suffix}")

    return logs
