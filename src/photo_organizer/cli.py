"""Command-line interface for photo_organizer."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from importlib import metadata as importlib_metadata
from pathlib import Path

from photo_organizer import __app_name__, __description__, __repository__, __version__
from photo_organizer.executor import (
    FileOperation,
    apply_operations,
    plan_organization_operations,
)
from photo_organizer.hashing import DuplicateGroup, find_duplicate_image_groups
from photo_organizer.logging_config import LOG_LEVEL_CHOICES, configure_logging
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
    if include_location_fields:
        for operation in operations:
            location = location_by_source.get(operation["source"])
            operation["location_status"] = location_status_by_source.get(
                operation["source"],
                "",
            )
            operation["city"] = location.city if location is not None else ""
            operation["state"] = location.state if location is not None else ""
            operation["country"] = location.country if location is not None else ""

    if path.suffix.lower() == ".csv":
        fieldnames = [
            "source",
            "destination",
            "action",
            "status",
            "observations",
        ]
        if include_location_fields:
            fieldnames.extend(["location_status", "city", "state", "country"])

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

    execution_group = organize_parser.add_argument_group("Execution")
    execution_group.add_argument(
        "--by",
        choices=["date"],
        default="date",
        help="Organization strategy. Currently only 'date' is supported.",
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
    organize_parser.set_defaults(reverse_geocode=False)

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
        if not args.output:
            parser.error(
                "organize requires --output DIR. Example: "
                "photo-organizer organize ./Photos --output ./OrganizedPhotos"
            )
        if args.report and Path(args.report).suffix.lower() not in {".json", ".csv"}:
            parser.error(
                "organize --report must end with .json or .csv. "
                "Example: --report audit.csv"
            )

        mode = "copy" if args.copy else "move"
        logger.info(
            "Execution started: organize source=%s output=%s mode=%s dry_run=%s plan_only=%s reverse_geocode=%s",
            args.source,
            args.output,
            mode,
            args.dry_run,
            args.plan,
            args.reverse_geocode,
        )
        try:
            operations = plan_organization_operations(
                args.source,
                args.output,
                mode=mode,
                reverse_geocode=args.reverse_geocode,
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
            args.by,
        )
        for operation in operations:
            logger.debug(
                "Plan item: action=%s source=%s destination=%s",
                operation.mode.upper(),
                operation.source,
                operation.destination,
            )

        if args.plan:
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
                "missing_gps_files": sum(
                    1
                    for operation in operations
                    if operation.location_status == "missing-gps"
                ),
            }
            logger.info(
                "Execution summary: mode=%s processed_files=%d ignored_files=%d error_files=%d fallback_files=%d location_files=%d missing_gps_files=%d",
                summary["mode"],
                summary["processed_files"],
                summary["ignored_files"],
                summary["error_files"],
                summary["fallback_files"],
                summary["location_files"],
                summary["missing_gps_files"],
            )
            logger.info(
                "Execution finished: organize processed_files=0 planned_files=%d",
                len(operations),
            )
            return 0

        if args.dry_run:
            logger.info("DRY-RUN enabled: no files will be changed")

        logs = apply_operations(operations, dry_run=args.dry_run)
        for line in logs:
            if line.startswith("[ERROR]"):
                logger.error(line)
            else:
                logger.info(line)

        error_files = sum(1 for line in logs if line.startswith("[ERROR]"))
        processed_files = len(logs) - error_files
        summary_mode = "dry-run" if args.dry_run else "execute"
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
            "missing_gps_files": sum(
                1
                for operation in operations
                if operation.location_status == "missing-gps"
            ),
        }
        logger.info(
            "Execution summary: mode=%s processed_files=%d ignored_files=%d error_files=%d fallback_files=%d location_files=%d missing_gps_files=%d",
            summary["mode"],
            summary["processed_files"],
            summary["ignored_files"],
            summary["error_files"],
            summary["fallback_files"],
            summary["location_files"],
            summary["missing_gps_files"],
        )

        if args.report:
            _write_execution_report(
                args.report,
                logs,
                summary,
                operations,
                include_location_fields=args.reverse_geocode,
            )
            logger.info("Execution report written: path=%s", args.report)

        logger.info("Execution finished: organize processed_files=%d", processed_files)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
