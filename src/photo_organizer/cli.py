"""Command-line interface for photo_organizer."""

from __future__ import annotations

import argparse
from importlib import metadata as importlib_metadata

from photo_organizer import __app_name__, __description__, __repository__, __version__


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(format_version_info())
        return 0

    if args.command == "scan":
        print(f"[INFO] Scanning directory: {args.source}")
        return 0

    if args.command == "organize":
        print(
            f"[INFO] Organizing photos from {args.source} to {args.output} by {args.by}"
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
