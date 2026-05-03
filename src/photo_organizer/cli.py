"""Command-line interface for photo_organizer."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from importlib import metadata as importlib_metadata
from pathlib import Path

from photo_organizer import __app_name__, __description__, __repository__, __version__
from photo_organizer.config import ConfigurationError, load_organization_config
from photo_organizer.executor import (
    FileOperation,
    apply_operations,
    plan_organization_operations,
)
from photo_organizer.hashing import DuplicateGroup, find_duplicate_image_groups
from photo_organizer.logging_config import LOG_LEVEL_CHOICES, configure_logging
from photo_organizer.metadata import (
    DATE_HEURISTICS_DEFAULT,
    RECONCILIATION_POLICY_CHOICES,
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
        str(operation.source): (
            "resolved"
            if operation.location is not None
            else operation.location_status
        )
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

        if include_location_fields:
            location = location_by_source.get(operation["source"])
            operation["location_status"] = location_status_by_source.get(
                operation["source"],
                "",
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
        ]
        if include_location_fields:
            fieldnames.extend(
                [
                    "location_status",
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
    parser = argparse.ArgumentParser(
        prog="photo-organizer",
        description="Organize photo files by date metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  photo-organizer scan ./Photos
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
        description="Scan a directory recursively for supported image files.",
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
        description="Find supported image files with identical content hashes.",
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

    organize_parser = subparsers.add_parser(
        "organize",
        help="Copy or move photos into date-based folders.",
        description="Organize supported image files into YYYY/MM/DD folders.",
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
        logger.info("Execution started: scan source=%s", args.source)
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

    if args.command == "organize":
        try:
            config = load_organization_config(args.config) if args.config else None
        except ConfigurationError as exc:
            parser.error(f"invalid organize configuration: {exc}")

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

        logs = apply_operations(operations, dry_run=dry_run)
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
