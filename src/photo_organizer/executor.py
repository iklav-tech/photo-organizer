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
from photo_organizer.constants import (
    RAW_IMAGE_FILE_EXTENSIONS,
    raw_flow_name_for_extension,
    raw_format_name_for_extension,
)
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
    raw_format: str = ""
    raw_flow: str = ""
    dng_candidate: bool = False
    dng_candidate_reason: str = ""


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
    dng_candidates: bool = False,
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
        raw_format = raw_format_name_for_extension(image_path.suffix)
        raw_flow = raw_flow_name_for_extension(image_path.suffix)
        dng_candidate = (
            dng_candidates and image_path.suffix.lower() in RAW_IMAGE_FILE_EXTENSIONS
        )
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
                raw_format=raw_format,
                raw_flow=raw_flow,
                dng_candidate=dng_candidate,
                dng_candidate_reason=(
                    "RAW file selected for optional DNG interoperability workflow"
                    if dng_candidate
                    else ""
                ),
            )
        )

    return operations


def apply_operations(
    operations: list[FileOperation],
    dry_run: bool = False,
    heic_preview: bool = False,
    staging_dir: str | Path | None = None,
) -> list[str]:
    """Apply planned operations or simulate them when dry_run is True.

    When *staging_dir* is provided the files are first written into that
    directory, mirroring the final destination structure.  Only after **all**
    operations succeed are the staged files promoted (moved) to their real
    destinations.  If any operation fails the staging area is cleaned up and
    the final output directory is left completely untouched, preventing partial
    inconsistent state.

    The *staging_dir* is created automatically when it does not exist.  It is
    the caller's responsibility to ensure the path is on the same filesystem as
    the output directory so that the final promotion step can use atomic renames
    where possible.

    Returns one status line per operation, including failures, so callers can
    inspect per-item outcomes.
    """
    if dry_run:
        return _apply_operations_dry_run(operations)

    if staging_dir is not None:
        return _apply_operations_with_staging(
            operations,
            Path(staging_dir),
            heic_preview=heic_preview,
        )

    return _apply_operations_direct(operations, heic_preview=heic_preview)


def _apply_operations_dry_run(operations: list[FileOperation]) -> list[str]:
    """Return dry-run log lines without touching the filesystem."""
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
        logs.append(f"[DRY-RUN] {action} {operation.source} -> {destination}")
    return logs


def _apply_operations_direct(
    operations: list[FileOperation],
    *,
    heic_preview: bool = False,
) -> list[str]:
    """Write files directly to their final destinations."""
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

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)

            if operation.mode == "copy":
                shutil.copy2(operation.source, destination)
            else:
                _move_file_after_successful_copy(operation.source, destination)
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
            _try_generate_heic_preview(destination)

        logs.append(f"[INFO] {line_suffix}")

    return logs


def _apply_operations_with_staging(
    operations: list[FileOperation],
    staging_dir: Path,
    *,
    heic_preview: bool = False,
) -> list[str]:
    """Copy files into *staging_dir*, then promote to final destinations.

    The staging directory mirrors the final destination tree.  Every file is
    written to ``staging_dir / <relative-destination-path>`` first.  If all
    copies succeed the staged files are moved to their real destinations.  On
    any failure the staging area is removed and the final output is untouched.
    """
    staging_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Staging enabled: staging_dir=%s", staging_dir)

    logs: list[str] = []
    reserved_destinations: set[Path] = set()

    # Resolve all final destinations up-front so conflict suffixes are stable.
    resolved: list[tuple[FileOperation, Path]] = []
    for operation in operations:
        destination = _resolve_available_operation_destination(
            operation.destination,
            operation.related_sidecars,
            reserved_destinations,
        )
        reserved_destinations.add(destination)
        for sidecar in operation.related_sidecars:
            reserved_destinations.add(_sidecar_destination(destination, sidecar))
        resolved.append((operation, destination))

    # Phase 1 – write everything into the staging area.
    staged: list[tuple[FileOperation, Path, Path]] = []  # (op, staged_path, final_dest)
    failed = False
    for operation, final_destination in resolved:
        action = operation.mode.upper()
        # Derive the staging path by replacing the output root prefix with the
        # staging root.  We use the full absolute path as a sub-path inside the
        # staging dir so that files from different output sub-trees never clash.
        staged_destination = _staging_path_for(staging_dir, final_destination)
        line_suffix = f"{action} {operation.source} -> {final_destination}"

        try:
            staged_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(operation.source, staged_destination)
            for sidecar in operation.related_sidecars:
                staged_sidecar = staged_destination.with_suffix(sidecar.suffix)
                shutil.copy2(sidecar, staged_sidecar)
        except Exception as exc:
            logger.error(
                "Staging failed: source=%s staged=%s error=%s",
                operation.source,
                staged_destination,
                exc,
            )
            logs.append(f"[ERROR] {line_suffix} (error: {exc})")
            failed = True
            continue

        staged.append((operation, staged_destination, final_destination))
        logs.append(f"[STAGED] {line_suffix}")

    if failed:
        # Clean up the staging area; leave the final output untouched.
        _cleanup_staging(staging_dir)
        logger.warning(
            "Staging aborted: errors occurred, staging area cleaned up, "
            "final output directory was not modified"
        )
        # Replace STAGED lines with ERROR for the failed items; the error lines
        # are already present.  Convert successful STAGED lines to ERROR too so
        # the caller knows nothing was committed.
        final_logs: list[str] = []
        for line in logs:
            if line.startswith("[STAGED]"):
                _, rest = line.split("] ", maxsplit=1)
                final_logs.append(f"[ERROR] {rest} (error: staging aborted due to earlier failure)")
            else:
                final_logs.append(line)
        return final_logs

    # Phase 2 – promote staged files to their final destinations.
    logger.info(
        "Staging complete: promoting %d file(s) to final destinations",
        len(staged),
    )
    promotion_logs: list[str] = []
    for operation, staged_path, final_destination in staged:
        action = operation.mode.upper()
        line_suffix = f"{action} {operation.source} -> {final_destination}"
        try:
            final_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staged_path), final_destination)
            for sidecar in operation.related_sidecars:
                staged_sidecar = staged_path.with_suffix(sidecar.suffix)
                sidecar_destination = _sidecar_destination(final_destination, sidecar)
                shutil.move(str(staged_sidecar), sidecar_destination)

            # Remove source only after successful promotion for move mode.
            if operation.mode == "move":
                try:
                    operation.source.unlink(missing_ok=True)
                    for sidecar in operation.related_sidecars:
                        sidecar.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning(
                        "Could not remove source after staged move: "
                        "source=%s error=%s",
                        operation.source,
                        exc,
                    )
        except Exception as exc:
            logger.error(
                "Promotion failed: staged=%s destination=%s error=%s",
                staged_path,
                final_destination,
                exc,
            )
            promotion_logs.append(f"[ERROR] {line_suffix} (error: promotion failed: {exc})")
            continue

        if heic_preview:
            _try_generate_heic_preview(final_destination)

        promotion_logs.append(f"[INFO] {line_suffix}")

    # Clean up the (now empty) staging area.
    _cleanup_staging(staging_dir)
    logger.info("Staging area cleaned up: staging_dir=%s", staging_dir)
    return promotion_logs


def _staging_path_for(staging_dir: Path, final_destination: Path) -> Path:
    """Map a final destination path into the staging directory tree.

    Uses the absolute path of the destination as a sub-path inside the staging
    root so that files from different output sub-trees never collide.
    """
    abs_dest = final_destination.resolve()
    # Strip the leading separator so Path / works correctly.
    relative = Path(*abs_dest.parts[1:]) if abs_dest.parts else abs_dest
    return staging_dir / relative


def _cleanup_staging(staging_dir: Path) -> None:
    """Remove the staging directory tree, logging but not raising on errors."""
    try:
        shutil.rmtree(staging_dir, ignore_errors=True)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to clean up staging dir: path=%s error=%s", staging_dir, exc)


def _try_generate_heic_preview(destination: Path) -> None:
    """Attempt HEIC preview generation, logging warnings on failure."""
    preview_destination = build_heic_preview_destination(destination)
    try:
        preview_path = generate_heic_preview(destination, preview_destination)
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
