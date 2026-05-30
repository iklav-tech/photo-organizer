"""Backend adapter used by the GUI.

This module intentionally delegates to existing photo_organizer services instead
of reimplementing scanning, duplicate detection, planning or execution rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from photo_organizer.executor import (
    FileOperation,
    apply_operations,
    plan_organization_operations,
)
from photo_organizer.constants import IMAGE_FORMATS
from photo_organizer.hashing import DuplicateGroup, find_duplicate_image_groups
from photo_organizer.gui.session import MetadataHealth, MetadataRatio
from photo_organizer.metadata import (
    DATE_HEURISTICS_DEFAULT,
    extract_camera_profile,
    extract_gps_coordinates,
    resolve_best_available_datetime,
)
from photo_organizer.scanner import find_image_files


@dataclass(frozen=True)
class GuiSettings:
    source: str
    output: str
    mode: str
    dry_run: bool
    organization_strategy: str


@dataclass(frozen=True)
class GuiScanMetrics:
    """Summary values derived from a backend scan result."""

    total_files: int
    total_size_bytes: int
    by_extension: dict[str, int]
    by_format: dict[str, int]


class OrganizerAdapter:
    """Thin adapter around the existing backend services."""

    def scan(self, source: str) -> list[Path]:
        return find_image_files(source, recursive=True)

    def scan_metrics(self, files: list[Path]) -> GuiScanMetrics:
        total_size_bytes = 0
        by_extension: dict[str, int] = {}
        by_format: dict[str, int] = {}
        for path in files:
            extension = path.suffix.lower() or "<none>"
            by_extension[extension] = by_extension.get(extension, 0) + 1
            format_name = _format_name_for_extension(extension)
            by_format[format_name] = by_format.get(format_name, 0) + 1
            try:
                total_size_bytes += path.stat().st_size
            except OSError:
                continue
        return GuiScanMetrics(
            total_files=len(files),
            total_size_bytes=total_size_bytes,
            by_extension=dict(sorted(by_extension.items())),
            by_format=dict(sorted(by_format.items())),
        )

    def metadata_health(self, files: list[Path]) -> MetadataHealth:
        total = len(files)
        if total == 0:
            return MetadataHealth()

        gps_present = 0
        timestamp_consistent = 0
        camera_profiles = 0

        for path in files:
            try:
                if extract_gps_coordinates(path) is not None:
                    gps_present += 1
            except Exception:
                pass

            try:
                resolved = resolve_best_available_datetime(path)
                if (
                    resolved.reconciliation is None
                    or not resolved.reconciliation.conflict
                ):
                    timestamp_consistent += 1
            except Exception:
                pass

            try:
                if extract_camera_profile(path):
                    camera_profiles += 1
            except Exception:
                pass

        return MetadataHealth(
            gps_presence=MetadataRatio(gps_present, total),
            timestamp_consistency=MetadataRatio(timestamp_consistent, total),
            camera_profiles=MetadataRatio(camera_profiles, total),
        )

    def find_duplicates(self, source: str) -> list[DuplicateGroup]:
        return find_duplicate_image_groups(source, recursive=True)

    def plan(self, settings: GuiSettings) -> list[FileOperation]:
        plan_result = plan_organization_operations(
            settings.source,
            settings.output,
            mode=settings.mode,
            organization_strategy=settings.organization_strategy,
            reverse_geocode=settings.organization_strategy
            in {"location", "location-date", "city-state-month"},
            reconciliation_policy="precedence",
            date_heuristics=DATE_HEURISTICS_DEFAULT,
            location_inference=True,
        )
        return plan_result[0] if isinstance(plan_result, tuple) else plan_result

    def execute(self, settings: GuiSettings) -> list[str]:
        operations = self.plan(settings)
        return apply_operations(
            operations,
            dry_run=settings.dry_run,
            conflict_quarantine_dir=Path(settings.output) / ".quarantine",
        )


def _format_name_for_extension(extension: str) -> str:
    for image_format in IMAGE_FORMATS:
        if extension in image_format.extensions:
            return image_format.name
    return "Unknown"
