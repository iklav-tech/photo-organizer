"""Command-line interface for photo_organizer."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from photo_organizer import __app_name__, __description__, __repository__, __version__
from photo_organizer.config import ConfigurationError, load_organization_config
from photo_organizer.constants import supported_image_extensions_text
from photo_organizer.correction_manifest import (
    CORRECTION_PRIORITY_CHOICES,
    CorrectionApplication,
    CorrectionManifestError,
    correction_for_file,
    load_correction_manifest,
)
from photo_organizer.executor import (
    FileOperation,
    apply_operations,
    plan_organization_operations,
)
from photo_organizer.geocoding import reverse_geocode_coordinates
from photo_organizer.hashing import DuplicateGroup, find_duplicate_image_groups
from photo_organizer.logging_config import LOG_LEVEL_CHOICES, configure_logging
from photo_organizer.metadata import (
    DATE_HEURISTICS_DEFAULT,
    RECONCILIATION_POLICY_CHOICES,
    extract_camera_profile,
    extract_embedded_xmp_metadata,
    extract_exif_metadata,
    extract_heif_container_metadata,
    extract_external_location_manifest,
    extract_gps_coordinates,
    extract_iptc_iim_location,
    extract_iptc_iim_metadata,
    extract_png_metadata,
    extract_xmp_sidecar_metadata,
    extract_xmp_textual_location,
    infer_location_from_batch,
    infer_location_from_folder,
    resolve_best_available_datetime,
    validate_clock_offset,
)
from photo_organizer.naming import validate_filename_pattern
from photo_organizer.scanner import find_image_files, is_supported_image_file


logger = logging.getLogger(__name__)


def _count_ignored_files(source: str) -> int:
    root = Path(source)
    return sum(
        1
        for path in root.rglob("*")
        if path.is_file() and not is_supported_image_file(path)
    )


def _report_item_from_operation_log(line: str) -> dict[str, str]:
    level, details = line.split("] ", maxsplit=1)
    marker = level.removeprefix("[")
    observations = ""

    if marker == "ERROR" and " (error: " in details:
        details, error_text = details.rsplit(" (error: ", maxsplit=1)
        observations = error_text.removesuffix(")")

    action, paths = details.split(" ", maxsplit=1)
    source, destination = paths.split(" -> ", maxsplit=1)
    status = {
        "DRY-RUN": "dry-run",
        "ERROR": "error",
        "INFO": "success",
    }.get(marker, marker.lower())

    if marker == "DRY-RUN":
        observations = "simulated; no filesystem changes applied"

    return {
        "source": source,
        "destination": destination,
        "action": action.lower(),
        "status": status,
        "observations": observations,
    }


def _report_raw_value(value: object) -> str:
    if value == "":
        return ""
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)


def _provenance_report_fields(prefix: str, provenance) -> dict[str, str]:
    if provenance is None:
        return {
            f"{prefix}_source": "",
            f"{prefix}_field": "",
            f"{prefix}_confidence": "",
            f"{prefix}_raw_value": "",
        }
    return {
        f"{prefix}_source": provenance.source,
        f"{prefix}_field": provenance.field,
        f"{prefix}_confidence": provenance.confidence,
        f"{prefix}_raw_value": _report_raw_value(provenance.raw_value),
    }


def _write_execution_report(
    report_path: str | Path,
    operation_logs: list[str],
    summary: dict[str, int | str],
    planned_operations: list[FileOperation] | None = None,
    include_location_fields: bool = False,
) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    operations = [
        _report_item_from_operation_log(line)
        for line in operation_logs
    ]
    location_by_source = {
        str(operation.source): operation.location
        for operation in planned_operations or []
        if operation.location is not None
    }
    location_status_by_source = {
        str(operation.source): operation.location_status
        for operation in planned_operations or []
    }
    coordinates_by_source = {
        str(operation.source): operation.coordinates
        for operation in planned_operations or []
        if operation.coordinates is not None
    }
    planned_operation_by_source = {
        str(operation.source): operation
        for operation in planned_operations or []
    }
    for operation in operations:
        planned_operation = planned_operation_by_source.get(operation["source"])
        if (
            planned_operation is not None
            and planned_operation.text_normalization_observations
        ):
            normalization_note = "text normalization: " + " | ".join(
                planned_operation.text_normalization_observations
            )
            operation["observations"] = (
                f"{operation['observations']}; {normalization_note}"
                if operation["observations"]
                else normalization_note
            )
        if (
            planned_operation is not None
            and planned_operation.date_reconciliation is not None
            and planned_operation.date_reconciliation.conflict
        ):
            reconciliation = planned_operation.date_reconciliation
            reconciliation_note = (
                "date reconciliation: "
                f"policy={reconciliation.policy}; "
                f"winner={reconciliation.selected.provenance.label}; "
                f"reason={reconciliation.reason}; "
                f"conflicting_sources={', '.join(reconciliation.conflicting_sources)}"
            )
            operation["observations"] = (
                f"{operation['observations']}; {reconciliation_note}"
                if operation["observations"]
                else reconciliation_note
            )
        if planned_operation is not None and planned_operation.correction_manifest is not None:
            correction = planned_operation.correction_manifest
            correction_note = (
                "correction manifest: "
                f"path={correction.source_path}; "
                f"selectors={', '.join(correction.selectors)}"
            )
            if correction.event_name:
                correction_note += f"; event={correction.event_name}"
            if correction.clock_offset:
                correction_note += f"; clock_offset={correction.clock_offset}"
                # Surface the original (pre-correction) datetime when available
                # in the provenance raw_value so the report preserves it.
                prov = planned_operation.date_provenance
                if (
                    prov is not None
                    and isinstance(prov.raw_value, dict)
                    and "base_value" in prov.raw_value
                ):
                    correction_note += f"; original_datetime={prov.raw_value['base_value']}"
            operation["observations"] = (
                f"{operation['observations']}; {correction_note}"
                if operation["observations"]
                else correction_note
            )
        operation.update(
            _provenance_report_fields(
                "date",
                planned_operation.date_provenance
                if planned_operation is not None
                else None,
            )
        )
        operation["date_kind"] = (
            planned_operation.date_kind if planned_operation is not None else ""
        )
        operation["event_name"] = (
            planned_operation.correction_manifest.event_name
            if planned_operation is not None
            and planned_operation.correction_manifest is not None
            and planned_operation.correction_manifest.event_name is not None
            else ""
        )

        if include_location_fields:
            location = location_by_source.get(operation["source"])
            operation["location_status"] = location_status_by_source.get(
                operation["source"],
                "",
            )
            operation["location_kind"] = (
                planned_operation.location_kind
                if planned_operation is not None
                else ""
            )
            operation["organization_fallback"] = (
                planned_operation.organization_fallback
                if planned_operation is not None
                else False
            )
            coordinates = coordinates_by_source.get(operation["source"])
            operation["latitude"] = (
                coordinates.latitude if coordinates is not None else ""
            )
            operation["longitude"] = (
                coordinates.longitude if coordinates is not None else ""
            )
            operation["city"] = location.city if location is not None else ""
            operation["state"] = location.state if location is not None else ""
            operation["country"] = location.country if location is not None else ""
            operation.update(
                _provenance_report_fields(
                    "gps",
                    coordinates.provenance if coordinates is not None else None,
                )
            )
            operation.update(
                _provenance_report_fields(
                    "location",
                    planned_operation.location_provenance
                    if planned_operation is not None
                    else None,
                )
            )

    if path.suffix.lower() == ".csv":
        fieldnames = [
            "source",
            "destination",
            "action",
            "status",
            "observations",
            "date_source",
            "date_field",
            "date_confidence",
            "date_raw_value",
            "date_kind",
            "event_name",
        ]
        if include_location_fields:
            fieldnames.extend(
                [
                    "location_status",
                    "location_kind",
                    "organization_fallback",
                    "latitude",
                    "longitude",
                    "city",
                    "state",
                    "country",
                    "gps_source",
                    "gps_field",
                    "gps_confidence",
                    "gps_raw_value",
                    "location_source",
                    "location_field",
                    "location_confidence",
                    "location_raw_value",
                ]
            )

        with path.open("w", encoding="utf-8", newline="") as report_file:
            writer = csv.DictWriter(
                report_file,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            writer.writerows(operations)
        return

    if path.suffix.lower() != ".json":
        raise ValueError("Report path must end with .json or .csv")

    report = {
        "summary": summary,
        "operations": operations,
    }
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _duplicate_group_to_report_item(
    group_id: int,
    group: DuplicateGroup,
) -> dict[str, object]:
    paths = [str(group.original), *(str(path) for path in group.duplicates)]
    return {
        "group_id": group_id,
        "hash": group.content_hash,
        "quantity": len(paths),
        "original": str(group.original),
        "duplicates": [str(path) for path in group.duplicates],
        "paths": paths,
    }


def _write_dedupe_report(
    report_path: str | Path,
    groups: list[DuplicateGroup],
) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    group_items = [
        _duplicate_group_to_report_item(group_id, group)
        for group_id, group in enumerate(groups, start=1)
    ]
    summary = {
        "duplicate_groups": len(groups),
        "duplicate_files": sum(len(group.duplicates) for group in groups),
        "total_files_in_duplicate_groups": sum(
            int(item["quantity"]) for item in group_items
        ),
    }

    if path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8", newline="") as report_file:
            writer = csv.DictWriter(
                report_file,
                fieldnames=[
                    "group_id",
                    "hash",
                    "quantity",
                    "role",
                    "path",
                ],
            )
            writer.writeheader()
            for item in group_items:
                writer.writerow(
                    {
                        "group_id": item["group_id"],
                        "hash": item["hash"],
                        "quantity": item["quantity"],
                        "role": "original",
                        "path": item["original"],
                    }
                )
                for duplicate in item["duplicates"]:
                    writer.writerow(
                        {
                            "group_id": item["group_id"],
                            "hash": item["hash"],
                            "quantity": item["quantity"],
                            "role": "duplicate",
                            "path": duplicate,
                        }
                    )
        return

    if path.suffix.lower() != ".json":
        raise ValueError("Report path must end with .json or .csv")

    report = {
        "summary": summary,
        "duplicate_groups": group_items,
    }
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _inspect_serializable(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[no-any-return]
    if isinstance(value, tuple):
        return [_inspect_serializable(item) for item in value]
    if isinstance(value, dict):
        return {key: _inspect_serializable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_inspect_serializable(item) for item in value]
    try:
        json.dumps(value)
    except TypeError:
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return str(value)
    return value


def _inspect_source_item(source: str, fields: dict[str, Any]) -> dict[str, object]:
    visible_fields = {
        key: value
        for key, value in fields.items()
        if value not in (None, "", {}, [])
        and key not in {"XMPFieldSources", "XMPNamespaces", "PNGFieldSources"}
    }
    return {
        "source": source,
        "exists": bool(visible_fields),
        "fields": _inspect_serializable(visible_fields),
    }


def _inspect_candidate_item(candidate) -> dict[str, object]:
    return {
        "value": candidate.value.isoformat()
        if hasattr(candidate.value, "isoformat")
        else str(candidate.value),
        "source": candidate.provenance.source,
        "field": candidate.provenance.field,
        "confidence": candidate.provenance.confidence,
        "raw_value": _inspect_serializable(candidate.provenance.raw_value),
        "role": candidate.role,
        "date_kind": candidate.date_kind,
        "used_fallback": candidate.used_fallback,
    }


def _inspect_provenance_item(provenance) -> dict[str, object] | None:
    if provenance is None:
        return None
    return {
        "source": provenance.source,
        "field": provenance.field,
        "confidence": provenance.confidence,
        "raw_value": _inspect_serializable(provenance.raw_value),
    }


def _global_clock_offset_correction(
    source_path: Path,
    clock_offset: str | None,
    correction_priority: str | None,
) -> CorrectionApplication | None:
    if clock_offset is None:
        return None
    return CorrectionApplication(
        source_path=source_path,
        selectors=("global:clock_offset",),
        clock_offset=clock_offset,
        priority=correction_priority or "highest",
    )


def _merge_global_clock_offset(
    source_path: Path,
    correction,
    clock_offset: str | None,
    correction_priority: str | None,
):
    if clock_offset is None:
        return correction
    if correction is None:
        return _global_clock_offset_correction(
            source_path,
            clock_offset,
            correction_priority,
        )
    if correction.clock_offset is not None:
        return correction
    return CorrectionApplication(
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


def _inspect_location(
    path: Path,
    reverse_geocode: bool,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    sources: list[dict[str, object]] = []
    coordinates = extract_gps_coordinates(path)
    if coordinates is not None:
        sources.append(
            {
                "source": coordinates.provenance.source
                if coordinates.provenance is not None
                else "GPS",
                "exists": True,
                "field": coordinates.provenance.field
                if coordinates.provenance is not None
                else "",
                "confidence": coordinates.provenance.confidence
                if coordinates.provenance is not None
                else "",
                "raw_value": _inspect_serializable(coordinates.provenance.raw_value)
                if coordinates.provenance is not None
                else {},
                "fields": {
                    "latitude": coordinates.latitude,
                    "longitude": coordinates.longitude,
                },
            }
        )

    textual_resolvers = (
        extract_iptc_iim_location,
        extract_xmp_textual_location,
        extract_external_location_manifest,
        infer_location_from_folder,
        infer_location_from_batch,
    )
    textual_matches = []
    for resolver in textual_resolvers:
        match = resolver(path)
        if match is None:
            continue
        location_fields, provenance = match
        textual_matches.append(match)
        sources.append(
            {
                "source": provenance.source,
                "exists": True,
                "field": provenance.field,
                "confidence": provenance.confidence,
                "raw_value": _inspect_serializable(provenance.raw_value),
                "fields": _inspect_serializable(location_fields),
            }
        )

    if coordinates is not None and reverse_geocode:
        location = reverse_geocode_coordinates(coordinates)
        if location is not None:
            return {
                "status": "resolved",
                "kind": "gps",
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude,
                "city": location.city,
                "state": location.state,
                "country": location.country,
                "provenance": {
                    "source": "Reverse geocoding",
                    "field": "GPSLatitudeDecimal,GPSLongitudeDecimal",
                    "confidence": "medium",
                    "raw_value": {
                        "latitude": coordinates.latitude,
                        "longitude": coordinates.longitude,
                    },
                },
            }, sources

    if coordinates is not None:
        return {
            "status": "gps",
            "kind": "gps",
            "latitude": coordinates.latitude,
            "longitude": coordinates.longitude,
            "city": None,
            "state": None,
            "country": None,
            "provenance": _inspect_provenance_item(coordinates.provenance),
        }, sources

    if textual_matches:
        location_fields, provenance = textual_matches[0]
        return {
            "status": "inferred",
            "kind": "inferred",
            "latitude": None,
            "longitude": None,
            "city": location_fields.get("city"),
            "state": location_fields.get("state"),
            "country": location_fields.get("country"),
            "provenance": _inspect_provenance_item(provenance),
        }, sources

    return {
        "status": "missing",
        "kind": "none",
        "latitude": None,
        "longitude": None,
        "city": None,
        "state": None,
        "country": None,
        "provenance": None,
    }, sources


def _inspect_file(
    path: Path,
    source_root: Path,
    reconciliation_policy: str,
    date_heuristics: bool,
    correction_manifest,
    correction_priority: str | None,
    clock_offset: str | None,
    reverse_geocode: bool,
) -> dict[str, object]:
    exif_fields = extract_exif_metadata(path)
    xmp_embedded_fields = extract_embedded_xmp_metadata(path)
    xmp_sidecar_fields = extract_xmp_sidecar_metadata(path)
    iptc_fields = extract_iptc_iim_metadata(path)
    png_fields = extract_png_metadata(path)
    heif_container_fields = extract_heif_container_metadata(path)
    camera_profile = extract_camera_profile(path)
    correction = correction_for_file(
        correction_manifest,
        path,
        source_root,
        correction_priority,
        camera_profile,
    )
    correction = _merge_global_clock_offset(
        source_root,
        correction,
        clock_offset,
        correction_priority,
    )
    source_items = [
        _inspect_source_item("EXIF", exif_fields),
        _inspect_source_item("XMP embedded", xmp_embedded_fields),
        _inspect_source_item("XMP sidecar", xmp_sidecar_fields),
        _inspect_source_item("IPTC-IIM", iptc_fields),
        _inspect_source_item("PNG metadata", png_fields),
        _inspect_source_item("HEIF container", heif_container_fields),
        _inspect_source_item("Camera profile", camera_profile),
    ]

    date_error = None
    try:
        date_resolution = resolve_best_available_datetime(
            path,
            reconciliation_policy=reconciliation_policy,  # type: ignore[arg-type]
            date_heuristics=date_heuristics,
            correction=correction,
        )
        date_decision = {
            "status": "resolved",
            "value": date_resolution.value.isoformat(),
            "source": date_resolution.provenance.source
            if date_resolution.provenance is not None
            else "",
            "field": date_resolution.provenance.field
            if date_resolution.provenance is not None
            else "",
            "confidence": date_resolution.provenance.confidence
            if date_resolution.provenance is not None
            else "",
            "date_kind": date_resolution.date_kind,
            "used_fallback": date_resolution.used_fallback,
            "reconciliation_policy": reconciliation_policy,
            "reconciliation_reason": date_resolution.reconciliation.reason
            if date_resolution.reconciliation is not None
            else "",
            "conflict": date_resolution.reconciliation.conflict
            if date_resolution.reconciliation is not None
            else False,
        }
        date_candidates = [
            _inspect_candidate_item(candidate)
            for candidate in (
                date_resolution.reconciliation.candidates
                if date_resolution.reconciliation is not None
                else ()
            )
        ]
    except Exception as exc:
        date_error = str(exc)
        date_decision = {
            "status": "error",
            "value": None,
            "source": "",
            "field": "",
            "confidence": "",
            "date_kind": "",
            "used_fallback": False,
            "reconciliation_policy": reconciliation_policy,
            "reconciliation_reason": date_error,
            "conflict": False,
        }
        date_candidates = []

    location_decision, location_sources = _inspect_location(path, reverse_geocode)
    source_items.extend(location_sources)
    if correction is not None:
        source_items.append(
            {
                "source": "Correction manifest",
                "exists": True,
                "fields": {
                    "path": str(correction.source_path),
                    "selectors": list(correction.selectors),
                    "date": correction.date_value,
                    "timezone": correction.timezone,
                    "clock_offset": correction.clock_offset,
                    "city": correction.city,
                    "state": correction.state,
                    "country": correction.country,
                    "event": correction.event_name,
                },
            }
        )

    return {
        "path": str(path),
        "sources": source_items,
        "date": {
            "decision": date_decision,
            "candidates": date_candidates,
        },
        "location": {
            "decision": location_decision,
            "sources": location_sources,
        },
    }


def _write_inspect_report(
    report_path: str | Path,
    summary: dict[str, int],
    files: list[dict[str, object]],
) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(
            json.dumps(
                {"summary": summary, "files": files},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return

    if path.suffix.lower() != ".csv":
        raise ValueError("Report path must end with .json or .csv")

    with path.open("w", encoding="utf-8", newline="") as report_file:
        writer = csv.DictWriter(
            report_file,
            fieldnames=[
                "path",
                "sources",
                "date_status",
                "date_value",
                "date_source",
                "date_field",
                "date_confidence",
                "date_kind",
                "date_conflict",
                "location_status",
                "location_kind",
                "latitude",
                "longitude",
                "city",
                "state",
                "country",
            ],
        )
        writer.writeheader()
        for item in files:
            date_decision = item["date"]["decision"]  # type: ignore[index]
            location_decision = item["location"]["decision"]  # type: ignore[index]
            writer.writerow(
                {
                    "path": item["path"],
                    "sources": ", ".join(
                        str(source["source"])
                        for source in item["sources"]  # type: ignore[index]
                        if source.get("exists")
                    ),
                    "date_status": date_decision["status"],
                    "date_value": date_decision["value"],
                    "date_source": date_decision["source"],
                    "date_field": date_decision["field"],
                    "date_confidence": date_decision["confidence"],
                    "date_kind": date_decision["date_kind"],
                    "date_conflict": date_decision["conflict"],
                    "location_status": location_decision["status"],
                    "location_kind": location_decision["kind"],
                    "latitude": location_decision["latitude"],
                    "longitude": location_decision["longitude"],
                    "city": location_decision["city"],
                    "state": location_decision["state"],
                    "country": location_decision["country"],
                }
            )


def _explain_date_decision(item: dict[str, object]) -> dict[str, object]:
    decision = item["date"]["decision"]  # type: ignore[index]
    return {
        "value": decision["value"],
        "source": decision["source"],
        "field": decision["field"],
        "confidence": decision["confidence"],
        "date_kind": decision["date_kind"],
        "used_fallback": decision["used_fallback"],
        "reconciliation_policy": decision["reconciliation_policy"],
        "reconciliation_reason": decision["reconciliation_reason"],
        "conflict": decision["conflict"],
    }


def _explain_location_decision(item: dict[str, object]) -> dict[str, object]:
    decision = item["location"]["decision"]  # type: ignore[index]
    provenance = decision.get("provenance") or {}
    return {
        "status": decision["status"],
        "kind": decision["kind"],
        "latitude": decision["latitude"],
        "longitude": decision["longitude"],
        "city": decision["city"],
        "state": decision["state"],
        "country": decision["country"],
        "source": provenance.get("source", "") if isinstance(provenance, dict) else "",
        "field": provenance.get("field", "") if isinstance(provenance, dict) else "",
        "confidence": provenance.get("confidence", "")
        if isinstance(provenance, dict)
        else "",
        "raw_value": provenance.get("raw_value", {})
        if isinstance(provenance, dict)
        else {},
    }


def _explain_location_candidate(source: dict[str, object]) -> dict[str, object]:
    return {
        "source": source["source"],
        "field": source.get("field", ""),
        "confidence": source.get("confidence", ""),
        "value": _inspect_serializable(source.get("fields", {})),
        "raw_value": _inspect_serializable(
            source.get("raw_value", source.get("fields", {}))
        ),
    }


def _explain_item_from_inspect_item(item: dict[str, object]) -> dict[str, object]:
    return {
        "path": item["path"],
        "chosen_date": _explain_date_decision(item),
        "chosen_location": _explain_location_decision(item),
        "candidates": {
            "date": _inspect_serializable(item["date"]["candidates"]),  # type: ignore[index]
            "location": [
                _explain_location_candidate(source)
                for source in item["location"]["sources"]  # type: ignore[index]
            ],
        },
        "sources": _inspect_serializable(item["sources"]),
    }


def _write_explain_report(
    report_path: str | Path,
    summary: dict[str, int],
    files: list[dict[str, object]],
) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() != ".json":
        raise ValueError("Explain report path must end with .json")

    report = {
        "summary": summary,
        "files": [_explain_item_from_inspect_item(item) for item in files],
    }
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def format_version_info() -> str:
    """Render a Linux-style version output with project metadata."""
    app_name = __app_name__
    version = __version__
    description = __description__
    repository = __repository__
    issues = ""

    try:
        meta = importlib_metadata.metadata(app_name)
        app_name = meta.get("Name", app_name)
        version = meta.get("Version", version)
        description = meta.get("Summary", description)

        for key, value in meta.items():
            if key == "Project-URL":
                label, sep, url = value.partition(",")
                if sep and label.strip().lower() == "repository":
                    repository = url.strip() or repository
                if sep and label.strip().lower() == "issues":
                    issues = url.strip()
    except importlib_metadata.PackageNotFoundError:
        # Keep local constants when the package metadata is not installed.
        pass

    lines = [
        f"{app_name} {version}",
        description,
        f"Repository: {repository}",
    ]
    if issues:
        lines.append(f"Issues:     {issues}")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    supported_extensions = supported_image_extensions_text()
    parser = argparse.ArgumentParser(
        prog="photo-organizer",
        description="Organize photo files by date metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  photo-organizer scan ./Photos
  photo-organizer inspect ./Photos
  photo-organizer explain ./Photos --report explain.json
  photo-organizer dedupe ./Photos
  photo-organizer organize ./Photos --output ./OrganizedPhotos
  photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
  photo-organizer organize ./Photos --output ./OrganizedPhotos --report audit.json
""",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show project version and exit.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=LOG_LEVEL_CHOICES,
        help="Set logging verbosity (default: INFO).",
    )

    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser(
        "scan",
        help="List supported image files in a directory.",
        description=(
            "Scan a directory recursively for supported image files. "
            f"Supported extensions: {supported_extensions}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  photo-organizer scan ./Photos
  photo-organizer --log-level DEBUG scan ./Photos
""",
    )
    scan_parser.add_argument(
        "source",
        metavar="SOURCE",
        help="Directory to scan.",
    )

    dedupe_parser = subparsers.add_parser(
        "dedupe",
        help="List duplicate images in a directory by content hash.",
        description=(
            "Find supported image files with identical content hashes. "
            f"Supported extensions: {supported_extensions}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  photo-organizer dedupe ./Photos
  photo-organizer dedupe ./Photos --report duplicates.json
  photo-organizer dedupe ./Photos --read-only
  photo-organizer --log-level DEBUG dedupe ./Photos
""",
    )
    dedupe_parser.add_argument(
        "source",
        metavar="SOURCE",
        help="Directory to scan for duplicate images.",
    )
    dedupe_parser.add_argument(
        "--read-only",
        action="store_true",
        help="Only list duplicate groups without changing files (default behavior).",
    )
    dedupe_parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write a structured duplicate report to this .json or .csv path.",
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
        aliases=["audit-metadata"],
        help="Audit available metadata sources and final decisions.",
        description=(
            "Inspect supported image files and show available metadata sources "
            "plus final date and location decisions. "
            f"Supported extensions: {supported_extensions}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  photo-organizer inspect ./Photos
  photo-organizer inspect ./Photos --report metadata-audit.json
  photo-organizer inspect ./Photos --report metadata-audit.csv
  photo-organizer inspect ./Photos --correction-manifest corrections.yaml
""",
    )
    inspect_parser.add_argument(
        "source",
        metavar="SOURCE",
        help="Directory containing photos to inspect.",
    )
    inspect_parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write a structured metadata audit report to this .json or .csv path.",
    )
    inspect_parser.add_argument(
        "--reconciliation-policy",
        choices=RECONCILIATION_POLICY_CHOICES,
        default="precedence",
        help=(
            "Metadata conflict policy for date decisions: precedence, newest, "
            "oldest, or filesystem (default: precedence)."
        ),
    )
    inspect_parser.add_argument(
        "--correction-manifest",
        metavar="PATH",
        help="Read batch correction overrides from a .csv, .json, .yaml or .yml file.",
    )
    inspect_parser.add_argument(
        "--correction-priority",
        choices=CORRECTION_PRIORITY_CHOICES,
        default=None,
        help=(
            "Priority for correction manifest date overrides: highest, metadata "
            "or heuristic (default: manifest/default highest)."
        ),
    )
    inspect_parser.add_argument(
        "--clock-offset",
        metavar="OFFSET",
        default=None,
        help=(
            "Apply a fixed time offset to inspect corrected captured datetime. "
            "Accepted formats: +3h, -1d, +00:30, -5:45."
        ),
    )
    inspect_heuristics_group = inspect_parser.add_mutually_exclusive_group()
    inspect_heuristics_group.add_argument(
        "--date-heuristics",
        action="store_true",
        dest="date_heuristics",
        help="Enable low-confidence inferred date heuristics (default).",
    )
    inspect_heuristics_group.add_argument(
        "--no-date-heuristics",
        action="store_false",
        dest="date_heuristics",
        help="Disable inferred date heuristics.",
    )
    inspect_parser.set_defaults(date_heuristics=None)
    inspect_parser.add_argument(
        "--reverse-geocode",
        action="store_true",
        help="Resolve GPS coordinates into city, state and country during audit.",
    )

    explain_parser = subparsers.add_parser(
        "explain",
        help="Write an explainable decision report for each file.",
        description=(
            "Show the decision trail for each supported image file, including "
            "chosen date, chosen location, candidates, sources and confidence. "
            f"Supported extensions: {supported_extensions}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  photo-organizer explain ./Photos
  photo-organizer explain ./Photos --report explain.json
  photo-organizer explain ./Photos --reverse-geocode --report explain.json
  photo-organizer explain ./Photos --correction-manifest corrections.yaml --report explain.json
""",
    )
    explain_parser.add_argument(
        "source",
        metavar="SOURCE",
        help="Directory containing photos to explain.",
    )
    explain_parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write the explain report to this .json path.",
    )
    explain_parser.add_argument(
        "--reconciliation-policy",
        choices=RECONCILIATION_POLICY_CHOICES,
        default="precedence",
        help=(
            "Metadata conflict policy for date decisions: precedence, newest, "
            "oldest, or filesystem (default: precedence)."
        ),
    )
    explain_parser.add_argument(
        "--correction-manifest",
        metavar="PATH",
        help="Read batch correction overrides from a .csv, .json, .yaml or .yml file.",
    )
    explain_parser.add_argument(
        "--correction-priority",
        choices=CORRECTION_PRIORITY_CHOICES,
        default=None,
        help=(
            "Priority for correction manifest date overrides: highest, metadata "
            "or heuristic (default: manifest/default highest)."
        ),
    )
    explain_parser.add_argument(
        "--clock-offset",
        metavar="OFFSET",
        default=None,
        help=(
            "Apply a fixed time offset to explain corrected captured datetime. "
            "Accepted formats: +3h, -1d, +00:30, -5:45."
        ),
    )
    explain_heuristics_group = explain_parser.add_mutually_exclusive_group()
    explain_heuristics_group.add_argument(
        "--date-heuristics",
        action="store_true",
        dest="date_heuristics",
        help="Enable low-confidence inferred date heuristics (default).",
    )
    explain_heuristics_group.add_argument(
        "--no-date-heuristics",
        action="store_false",
        dest="date_heuristics",
        help="Disable inferred date heuristics.",
    )
    explain_parser.set_defaults(date_heuristics=None)
    explain_parser.add_argument(
        "--reverse-geocode",
        action="store_true",
        help="Resolve GPS coordinates into city, state and country in the report.",
    )

    organize_parser = subparsers.add_parser(
        "organize",
        help="Copy or move photos into date-based folders.",
        description=(
            "Organize supported image files into YYYY/MM/DD folders. "
            f"Supported extensions: {supported_extensions}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  photo-organizer organize ./Photos --output ./OrganizedPhotos
  photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
  photo-organizer organize ./Photos --output ./OrganizedPhotos --copy
  photo-organizer organize ./Photos --output ./OrganizedPhotos --name-pattern "{date:%Y%m%d}_{stem}{ext}"
  photo-organizer organize ./Photos --config organizer.yaml
  photo-organizer organize ./Photos --output ./OrganizedPhotos --by city-state-month
  photo-organizer organize ./Photos --output ./OrganizedPhotos --by location-date
  photo-organizer organize ./Photos --output ./OrganizedPhotos --report audit.csv
""",
    )
    path_group = organize_parser.add_argument_group("Paths")
    path_group.add_argument(
        "source",
        metavar="SOURCE",
        help="Directory containing photos to organize.",
    )
    path_group.add_argument(
        "--output",
        metavar="DIR",
        help="Directory where organized photos will be written.",
    )
    path_group.add_argument(
        "--config",
        metavar="PATH",
        help="Read organization rules from a .json, .yaml or .yml file.",
    )
    path_group.add_argument(
        "--correction-manifest",
        metavar="PATH",
        help="Read batch correction overrides from a .csv, .json, .yaml or .yml file.",
    )

    execution_group = organize_parser.add_argument_group("Execution")
    execution_group.add_argument(
        "--by",
        choices=["date", "location", "location-date", "city-state-month"],
        default=None,
        help=(
            "Organization strategy: date, location, location-date, or "
            "city-state-month."
        ),
    )
    execution_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate operations without changing files.",
    )
    execution_group.add_argument(
        "--plan",
        action="store_true",
        help="Show planned operations and exit without executing.",
    )
    execution_group.add_argument(
        "--name-pattern",
        metavar="PATTERN",
        help=(
            "Filename pattern. Supported fields: {date}, {stem}, {ext}, "
            "{original}. Example: '{date:%%Y%%m%%d}_{stem}{ext}'."
        ),
    )
    execution_group.add_argument(
        "--reconciliation-policy",
        choices=RECONCILIATION_POLICY_CHOICES,
        default=None,
        help=(
            "Metadata conflict policy for dates: precedence, newest, oldest, "
            "or filesystem (default: precedence)."
        ),
    )
    execution_group.add_argument(
        "--correction-priority",
        choices=CORRECTION_PRIORITY_CHOICES,
        default=None,
        help=(
            "Priority for correction manifest date overrides: highest, metadata "
            "or heuristic (default: manifest/default highest)."
        ),
    )
    execution_group.add_argument(
        "--clock-offset",
        metavar="OFFSET",
        default=None,
        help=(
            "Apply a fixed time offset to every file's captured datetime. "
            "Useful for correcting camera clock drift. "
            "Accepted formats: +3h, -1d, +00:30, -5:45. "
            "For negative offsets use the = form: --clock-offset=-1d. "
            "Per-file offsets in a correction manifest take precedence."
        ),
    )
    preview_group = execution_group.add_mutually_exclusive_group()
    preview_group.add_argument(
        "--heic-preview",
        action="store_true",
        dest="heic_preview",
        help="Generate optional JPEG previews for HEIC/HEIF files after organizing.",
    )
    preview_group.add_argument(
        "--no-heic-preview",
        action="store_false",
        dest="heic_preview",
        help="Disable optional HEIC/HEIF preview generation.",
    )
    organize_parser.set_defaults(heic_preview=None)
    heuristics_group = execution_group.add_mutually_exclusive_group()
    heuristics_group.add_argument(
        "--date-heuristics",
        action="store_true",
        dest="date_heuristics",
        help="Enable low-confidence inferred date heuristics (default).",
    )
    heuristics_group.add_argument(
        "--no-date-heuristics",
        action="store_false",
        dest="date_heuristics",
        help="Disable inferred date heuristics and require supported date metadata.",
    )
    organize_parser.set_defaults(date_heuristics=None)
    location_inference_group = execution_group.add_mutually_exclusive_group()
    location_inference_group.add_argument(
        "--location-inference",
        action="store_true",
        dest="location_inference",
        help="Enable inferred non-GPS location from textual metadata and context.",
    )
    location_inference_group.add_argument(
        "--no-location-inference",
        action="store_false",
        dest="location_inference",
        help="Disable inferred location and organize location strategies under UnknownLocation.",
    )
    organize_parser.set_defaults(location_inference=None)
    geocoding_group = execution_group.add_mutually_exclusive_group()
    geocoding_group.add_argument(
        "--reverse-geocode",
        action="store_true",
        help="Resolve GPS coordinates into city, state and country.",
    )
    geocoding_group.add_argument(
        "--no-reverse-geocode",
        action="store_false",
        dest="reverse_geocode",
        help="Disable reverse geocoding (default).",
    )
    organize_parser.set_defaults(reverse_geocode=None)

    report_group = organize_parser.add_argument_group("Audit report")
    report_group.add_argument(
        "--report",
        metavar="PATH",
        help="Write a structured execution report to this .json or .csv path.",
    )

    mode_arguments = organize_parser.add_argument_group("Operation mode")
    mode_group = mode_arguments.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of moving them.",
    )
    mode_group.add_argument(
        "--move",
        action="store_true",
        help="Move files (default behavior).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    if args.version:
        print(format_version_info())
        return 0

    if args.command == "scan":
        logger.info(
            "Execution started: scan source=%s supported_extensions=%s",
            args.source,
            supported_image_extensions_text(),
        )
        try:
            files = find_image_files(args.source, recursive=True)
        except FileNotFoundError:
            logger.error("Source directory does not exist: %s", args.source)
            logger.info("Execution finished: scan processed_files=0")
            return 1
        except NotADirectoryError:
            logger.error("Source path is not a directory: %s", args.source)
            logger.info("Execution finished: scan processed_files=0")
            return 1
        logger.info("Found image files: count=%d", len(files))
        logger.info("Execution finished: scan processed_files=%d", len(files))
        return 0

    if args.command == "dedupe":
        if args.report and Path(args.report).suffix.lower() not in {".json", ".csv"}:
            parser.error(
                "dedupe --report must end with .json or .csv. "
                "Example: --report duplicates.json"
            )

        logger.info(
            "Execution started: dedupe source=%s read_only=%s",
            args.source,
            True,
        )
        try:
            groups = find_duplicate_image_groups(args.source, recursive=True)
        except FileNotFoundError:
            logger.error("Source directory does not exist: %s", args.source)
            logger.info("Execution finished: dedupe duplicate_groups=0 duplicate_files=0")
            return 1
        except NotADirectoryError:
            logger.error("Source path is not a directory: %s", args.source)
            logger.info("Execution finished: dedupe duplicate_groups=0 duplicate_files=0")
            return 1

        if not groups:
            print("No duplicate images found.")
        else:
            for index, group in enumerate(groups, start=1):
                print(f"Duplicate group {index}:")
                print(f"  Hash: {group.content_hash}")
                print(f"  Quantity: {len(group.duplicates) + 1}")
                print(f"  Original: {group.original}")
                for duplicate in group.duplicates:
                    print(f"  Duplicate: {duplicate}")

        duplicate_files = sum(len(group.duplicates) for group in groups)
        logger.info(
            "Execution finished: dedupe duplicate_groups=%d duplicate_files=%d",
            len(groups),
            duplicate_files,
        )
        if args.report:
            _write_dedupe_report(args.report, groups)
            logger.info("Dedupe report written: path=%s", args.report)
        return 0

    if args.command in {"inspect", "audit-metadata", "explain"}:
        if args.command == "explain":
            if args.report and Path(args.report).suffix.lower() != ".json":
                parser.error(
                    "explain --report must end with .json. "
                    "Example: --report explain.json"
                )
        elif args.report and Path(args.report).suffix.lower() not in {".json", ".csv"}:
            parser.error(
                "inspect --report must end with .json or .csv. "
                "Example: --report metadata-audit.json"
            )
        if args.clock_offset is not None:
            try:
                validate_clock_offset(args.clock_offset)
            except ValueError as exc:
                parser.error(f"invalid --clock-offset: {exc}")

        try:
            correction_manifest = (
                load_correction_manifest(args.correction_manifest)
                if args.correction_manifest is not None
                else None
            )
        except (CorrectionManifestError, ValueError, json.JSONDecodeError) as exc:
            parser.error(f"invalid correction manifest: {exc}")

        date_heuristics = (
            args.date_heuristics
            if args.date_heuristics is not None
            else DATE_HEURISTICS_DEFAULT
        )
        logger.info("Execution started: %s source=%s", args.command, args.source)
        try:
            files = find_image_files(args.source, recursive=True)
        except FileNotFoundError:
            logger.error("Source directory does not exist: %s", args.source)
            logger.info("Execution finished: %s inspected_files=0", args.command)
            return 1
        except NotADirectoryError:
            logger.error("Source path is not a directory: %s", args.source)
            logger.info("Execution finished: %s inspected_files=0", args.command)
            return 1

        source_root = Path(args.source)
        inspected_files = [
            _inspect_file(
                path,
                source_root,
                args.reconciliation_policy,
                date_heuristics,
                correction_manifest,
                args.correction_priority,
                args.clock_offset,
                args.reverse_geocode,
            )
            for path in files
        ]
        summary = {
            "inspected_files": len(inspected_files),
            "date_resolved_files": sum(
                1
                for item in inspected_files
                if item["date"]["decision"]["status"] == "resolved"  # type: ignore[index]
            ),
            "location_resolved_files": sum(
                1
                for item in inspected_files
                if item["location"]["decision"]["status"]  # type: ignore[index]
                in {"gps", "resolved", "inferred"}
            ),
            "date_conflict_files": sum(
                1
                for item in inspected_files
                if item["date"]["decision"]["conflict"]  # type: ignore[index]
            ),
        }

        if args.command == "explain":
            explain_summary = {
                "explained_files": summary["inspected_files"],
                "date_resolved_files": summary["date_resolved_files"],
                "location_resolved_files": summary["location_resolved_files"],
                "date_conflict_files": summary["date_conflict_files"],
            }
            for item in inspected_files:
                explain_item = _explain_item_from_inspect_item(item)
                chosen_date = explain_item["chosen_date"]
                chosen_location = explain_item["chosen_location"]
                candidates = explain_item["candidates"]
                print(f"File: {explain_item['path']}")
                print(
                    "  Chosen date: "
                    f"{chosen_date['value'] or 'missing'} "
                    f"source={chosen_date['source'] or 'none'} "
                    f"confidence={chosen_date['confidence'] or 'none'}"
                )
                location_parts = ", ".join(
                    str(value)
                    for value in (
                        chosen_location["city"],
                        chosen_location["state"],
                        chosen_location["country"],
                    )
                    if value
                )
                if not location_parts and chosen_location["latitude"] is not None:
                    location_parts = (
                        f"{chosen_location['latitude']}, "
                        f"{chosen_location['longitude']}"
                    )
                print(
                    "  Chosen location: "
                    f"{location_parts or chosen_location['status']} "
                    f"source={chosen_location['source'] or 'none'} "
                    f"confidence={chosen_location['confidence'] or 'none'}"
                )
                print(
                    "  Candidates: "
                    f"date={len(candidates['date'])} "
                    f"location={len(candidates['location'])}"
                )

            if args.report:
                _write_explain_report(args.report, explain_summary, inspected_files)
                logger.info("Explain report written: path=%s", args.report)

            logger.info(
                "Execution finished: explain explained_files=%d",
                len(inspected_files),
            )
            return 0

        for item in inspected_files:
            date_decision = item["date"]["decision"]  # type: ignore[index]
            location_decision = item["location"]["decision"]  # type: ignore[index]
            source_names = ", ".join(
                str(source["source"])
                for source in item["sources"]  # type: ignore[index]
                if source.get("exists")
            )
            print(f"File: {item['path']}")
            print(f"  Sources: {source_names or 'none'}")
            for source in item["sources"]:  # type: ignore[index]
                if source.get("source") != "HEIF container" or not source.get("exists"):
                    continue
                fields = source.get("fields", {})
                if not isinstance(fields, dict):
                    continue
                unsupported = fields.get("unsupported_features") or []
                unsupported_text = ", ".join(str(value) for value in unsupported)
                print(
                    "  HEIF: "
                    f"status={fields.get('status', 'unknown')} "
                    f"images={fields.get('image_count', '')} "
                    f"selected_image={fields.get('selected_image_index', '')}"
                    + (f" unsupported={unsupported_text}" if unsupported_text else "")
                )
            print(
                "  Date: "
                f"{date_decision['status']} "
                f"{date_decision['value'] or ''} "
                f"({date_decision['source']}:{date_decision['field']})".strip()
            )
            location_value = ", ".join(
                str(value)
                for value in (
                    location_decision["city"],
                    location_decision["state"],
                    location_decision["country"],
                )
                if value
            )
            if not location_value and location_decision["latitude"] is not None:
                location_value = (
                    f"{location_decision['latitude']}, "
                    f"{location_decision['longitude']}"
                )
            print(
                "  Location: "
                f"{location_decision['status']} "
                f"{location_value}".rstrip()
            )

        if args.report:
            _write_inspect_report(args.report, summary, inspected_files)
            logger.info("Inspect report written: path=%s", args.report)

        logger.info(
            "Execution finished: inspect inspected_files=%d",
            len(inspected_files),
        )
        return 0

    if args.command == "organize":
        try:
            config = load_organization_config(args.config) if args.config else None
        except ConfigurationError as exc:
            parser.error(f"invalid organize configuration: {exc}")

        correction_manifest_path = (
            args.correction_manifest
            if args.correction_manifest is not None
            else config.correction_manifest
            if config is not None and config.correction_manifest is not None
            else None
        )
        correction_priority = (
            args.correction_priority
            if args.correction_priority is not None
            else config.correction_priority
            if config is not None and config.correction_priority is not None
            else None
        )
        try:
            correction_manifest = (
                load_correction_manifest(correction_manifest_path)
                if correction_manifest_path is not None
                else None
            )
        except (CorrectionManifestError, ValueError, json.JSONDecodeError) as exc:
            parser.error(f"invalid correction manifest: {exc}")

        output = args.output or (config.output if config is not None else None)
        strategy = (
            args.by
            or (config.organization_strategy if config is not None else None)
            or "date"
        )
        mode = (
            "copy"
            if args.copy
            else "move"
            if args.move
            else (
                config.mode
                if config is not None and config.mode is not None
                else "move"
            )
        )
        dry_run = args.dry_run or (
            config.dry_run
            if config is not None and config.dry_run is not None
            else False
        )
        plan_only = args.plan or (
            config.plan if config is not None and config.plan is not None else False
        )
        reverse_geocode = (
            args.reverse_geocode
            if args.reverse_geocode is not None
            else config.reverse_geocode
            if config is not None and config.reverse_geocode is not None
            else strategy in {"location", "location-date", "city-state-month"}
        )
        naming_pattern = (
            args.name_pattern
            if args.name_pattern is not None
            else config.naming_pattern
            if config is not None
            else None
        )
        destination_pattern = (
            config.destination_pattern if config is not None else None
        )
        reconciliation_policy = (
            args.reconciliation_policy
            if args.reconciliation_policy is not None
            else config.reconciliation_policy
            if config is not None and config.reconciliation_policy is not None
            else "precedence"
        )
        date_heuristics = (
            args.date_heuristics
            if args.date_heuristics is not None
            else config.date_heuristics
            if config is not None and config.date_heuristics is not None
            else DATE_HEURISTICS_DEFAULT
        )
        location_inference = (
            args.location_inference
            if args.location_inference is not None
            else config.location_inference
            if config is not None and config.location_inference is not None
            else True
        )
        clock_offset = (
            args.clock_offset
            if args.clock_offset is not None
            else config.clock_offset
            if config is not None and config.clock_offset is not None
            else None
        )
        heic_preview = (
            args.heic_preview
            if args.heic_preview is not None
            else config.heic_preview
            if config is not None and config.heic_preview is not None
            else False
        )

        if not output:
            parser.error(
                "organize requires --output DIR. Example: "
                "photo-organizer organize ./Photos --output ./OrganizedPhotos"
            )
        if args.report and Path(args.report).suffix.lower() not in {".json", ".csv"}:
            parser.error(
                "organize --report must end with .json or .csv. "
                "Example: --report audit.csv"
            )
        if (
            strategy in {"location", "location-date", "city-state-month"}
            and reverse_geocode is False
        ):
            parser.error(
                f"organize --by {strategy} requires reverse geocoding. "
                "Remove --no-reverse-geocode or use --by date."
            )
        if naming_pattern is not None:
            try:
                validate_filename_pattern(naming_pattern)
            except ValueError as exc:
                parser.error(f"invalid --name-pattern: {exc}")
        if clock_offset is not None:
            try:
                validate_clock_offset(clock_offset)
            except ValueError as exc:
                parser.error(f"invalid --clock-offset: {exc}")

        logger.info(
            "Execution started: organize source=%s output=%s mode=%s dry_run=%s plan_only=%s reverse_geocode=%s",
            args.source,
            output,
            mode,
            dry_run,
            plan_only,
            reverse_geocode,
        )
        try:
            operations = plan_organization_operations(
                args.source,
                output,
                mode=mode,
                reverse_geocode=reverse_geocode,
                organization_strategy=strategy,
                naming_pattern=naming_pattern,
                destination_pattern=destination_pattern,
                reconciliation_policy=reconciliation_policy,
                date_heuristics=date_heuristics,
                location_inference=location_inference,
                correction_manifest=correction_manifest,
                correction_priority=correction_priority,
                clock_offset=clock_offset,
            )
            ignored_files = _count_ignored_files(args.source)
        except FileNotFoundError:
            logger.error("Source directory does not exist: %s", args.source)
            logger.info("Execution finished: organize processed_files=0")
            return 1
        except NotADirectoryError:
            logger.error("Source path is not a directory: %s", args.source)
            logger.info("Execution finished: organize processed_files=0")
            return 1

        logger.info(
            "Generated execution plan: operations=%d strategy=%s",
            len(operations),
            strategy,
        )
        for operation in operations:
            logger.debug(
                "Plan item: action=%s source=%s destination=%s",
                operation.mode.upper(),
                operation.source,
                operation.destination,
            )

        if plan_only:
            logger.info("Plan-only mode enabled: no files will be changed")
            summary: dict[str, int | str] = {
                "mode": "plan",
                "processed_files": 0,
                "ignored_files": ignored_files,
                "error_files": 0,
                "fallback_files": sum(
                    1 for operation in operations if operation.date_fallback
                ),
                "location_files": sum(
                    1 for operation in operations if operation.location is not None
                ),
                "gps_files": sum(
                    1 for operation in operations if operation.coordinates is not None
                ),
                "missing_gps_files": sum(
                    1
                    for operation in operations
                    if operation.location_status == "missing-gps"
                ),
                "organization_fallback_files": sum(
                    1 for operation in operations if operation.organization_fallback
                ),
            }
            logger.info(
                "Execution summary: mode=%s processed_files=%d ignored_files=%d error_files=%d fallback_files=%d location_files=%d gps_files=%d missing_gps_files=%d organization_fallback_files=%d",
                summary["mode"],
                summary["processed_files"],
                summary["ignored_files"],
                summary["error_files"],
                summary["fallback_files"],
                summary["location_files"],
                summary["gps_files"],
                summary["missing_gps_files"],
                summary["organization_fallback_files"],
            )
            logger.info(
                "Execution finished: organize processed_files=0 planned_files=%d",
                len(operations),
            )
            return 0

        if dry_run:
            logger.info("DRY-RUN enabled: no files will be changed")

        logs = apply_operations(
            operations,
            dry_run=dry_run,
            heic_preview=heic_preview,
        )
        for line in logs:
            if line.startswith("[ERROR]"):
                logger.error(line)
            else:
                logger.info(line)

        error_files = sum(1 for line in logs if line.startswith("[ERROR]"))
        processed_files = len(logs) - error_files
        summary_mode = "dry-run" if dry_run else "execute"
        fallback_files = sum(1 for operation in operations if operation.date_fallback)
        location_files = sum(
            1 for operation in operations if operation.location is not None
        )
        summary = {
            "mode": summary_mode,
            "processed_files": processed_files,
            "ignored_files": ignored_files,
            "error_files": error_files,
            "fallback_files": fallback_files,
            "location_files": location_files,
            "gps_files": sum(
                1 for operation in operations if operation.coordinates is not None
            ),
            "missing_gps_files": sum(
                1
                for operation in operations
                if operation.location_status == "missing-gps"
            ),
            "organization_fallback_files": sum(
                1 for operation in operations if operation.organization_fallback
            ),
        }
        logger.info(
            "Execution summary: mode=%s processed_files=%d ignored_files=%d error_files=%d fallback_files=%d location_files=%d gps_files=%d missing_gps_files=%d organization_fallback_files=%d",
            summary["mode"],
            summary["processed_files"],
            summary["ignored_files"],
            summary["error_files"],
            summary["fallback_files"],
            summary["location_files"],
            summary["gps_files"],
            summary["missing_gps_files"],
            summary["organization_fallback_files"],
        )

        if args.report:
            _write_execution_report(
                args.report,
                logs,
                summary,
                operations,
                include_location_fields=reverse_geocode,
            )
            logger.info("Execution report written: path=%s", args.report)

        logger.info("Execution finished: organize processed_files=%d", processed_files)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
