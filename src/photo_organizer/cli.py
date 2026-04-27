"""Command-line interface for photo_organizer."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from importlib import metadata as importlib_metadata
from pathlib import Path

from photo_organizer import __app_name__, __description__, __repository__, __version__
from photo_organizer.executor import apply_operations, plan_organization_operations
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
) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    operations = [
        _report_item_from_operation_log(line)
        for line in operation_logs
    ]

    if path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8", newline="") as report_file:
            writer = csv.DictWriter(
                report_file,
                fieldnames=[
                    "source",
                    "destination",
                    "action",
                    "status",
                    "observations",
                ],
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
        description="Organize photos by metadata and date.",
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
        help="Scan a directory for photo files.",
        description="Scan a directory recursively for photo files.",
    )
    scan_parser.add_argument(
        "source",
        help="Source directory to scan.",
    )

    organize_parser = subparsers.add_parser(
        "organize",
        help="Organize photos from source to output directory.",
        description="Organize photos by strategy into an output directory.",
    )
    organize_parser.add_argument(
        "source",
        help="Source directory containing photos.",
    )
    organize_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for organized photos.",
    )
    organize_parser.add_argument(
        "--by",
        choices=["date"],
        default="date",
        help="Organization strategy (default: date).",
    )
    organize_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate operations without changing files.",
    )
    organize_parser.add_argument(
        "--plan",
        action="store_true",
        help="Show planned operations and exit without executing.",
    )
    organize_parser.add_argument(
        "--report",
        help="Write a structured execution report to this .json or .csv path.",
    )
    mode_group = organize_parser.add_mutually_exclusive_group()
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

    if args.command == "organize":
        mode = "copy" if args.copy else "move"
        logger.info(
            "Execution started: organize source=%s output=%s mode=%s dry_run=%s plan_only=%s",
            args.source,
            args.output,
            mode,
            args.dry_run,
            args.plan,
        )
        try:
            operations = plan_organization_operations(args.source, args.output, mode=mode)
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
            }
            logger.info(
                "Execution summary: mode=%s processed_files=%d ignored_files=%d error_files=%d fallback_files=%d",
                summary["mode"],
                summary["processed_files"],
                summary["ignored_files"],
                summary["error_files"],
                summary["fallback_files"],
            )
            logger.info("Execution finished: organize processed_files=0 planned_files=%d", len(operations))
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
        summary = {
            "mode": summary_mode,
            "processed_files": processed_files,
            "ignored_files": ignored_files,
            "error_files": error_files,
            "fallback_files": fallback_files,
        }
        logger.info(
            "Execution summary: mode=%s processed_files=%d ignored_files=%d error_files=%d fallback_files=%d",
            summary["mode"],
            summary["processed_files"],
            summary["ignored_files"],
            summary["error_files"],
            summary["fallback_files"],
        )

        if args.report:
            _write_execution_report(args.report, logs, summary)
            logger.info("Execution report written: path=%s", args.report)

        logger.info("Execution finished: organize processed_files=%d", processed_files)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
