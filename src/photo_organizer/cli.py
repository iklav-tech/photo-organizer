"""Command-line interface for photo_organizer."""

from __future__ import annotations

import argparse
from importlib import metadata as importlib_metadata

from photo_organizer import __app_name__, __description__, __repository__, __version__
from photo_organizer.executor import apply_operations, plan_organization_operations
from photo_organizer.scanner import find_image_files


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

    if args.version:
        print(format_version_info())
        return 0

    if args.command == "scan":
        files = find_image_files(args.source, recursive=True)
        print(f"[INFO] Scanning directory: {args.source}")
        print(f"[INFO] Found {len(files)} image files")
        return 0

    if args.command == "organize":
        mode = "copy" if args.copy else "move"
        operations = plan_organization_operations(args.source, args.output, mode=mode)

        print(
            f"[INFO] Organizing photos from {args.source} to {args.output} by {args.by}"
        )
        if args.dry_run:
            print("[INFO] DRY-RUN enabled: no files will be changed")

        logs = apply_operations(operations, dry_run=args.dry_run)
        for line in logs:
            print(line)

        print(f"[INFO] Planned operations: {len(operations)}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
