"""Dashboard page with scan session metrics."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from photo_organizer.executor import FileOperation
from photo_organizer.gui.session import (
    MetadataHealth,
    MetadataRatio,
    SessionMetrics,
    SessionState,
)
from photo_organizer.gui.theme import SPACING, set_theme_role
from photo_organizer.gui.widgets import MetricCard
from photo_organizer.hashing import DuplicateGroup


class DashboardPage(QWidget):
    """Top-level dashboard fed by shared session state."""

    def __init__(
        self,
        session: SessionState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self._build_ui()
        self.session.source_directory_changed.connect(self._update_source_path)
        self.session.metrics_changed.connect(self.update_metrics)
        self.session.metadata_health_changed.connect(self.update_metadata_health)
        self.session.duplicate_groups_changed.connect(self.update_duplicate_conflicts)
        self.session.preview_operations_changed.connect(self.update_preview_conflicts)
        self._update_source_path(self.session.source_directory)
        self.update_metrics(self.session.metrics)
        self.update_metadata_health(self.session.metadata_health)
        self.update_duplicate_conflicts(self.session.duplicate_groups)
        self.update_preview_conflicts(self.session.preview_operations)

    def _build_ui(self) -> None:
        set_theme_role(self, "page")
        self.source_path_label = QLabel("SOURCE PATH: not selected")
        set_theme_role(self.source_path_label, "metadata")
        title = QLabel("Dashboard")
        set_theme_role(title, "headline")

        header = QVBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(SPACING.xs)
        header.addWidget(self.source_path_label)
        header.addWidget(title)

        self.total_files_card = MetricCard("TOTAL FILES")
        self.total_size_card = MetricCard("TOTAL SIZE")
        self.formats_card = MetricCard("SUPPORTED FORMATS")
        self.metadata_panel = MetadataIntegrityPanel()
        self.duplicates_panel = DuplicateConflictPanel()

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING.md)
        grid.setVerticalSpacing(SPACING.md)
        grid.addWidget(self.total_files_card, 0, 0)
        grid.addWidget(self.total_size_card, 0, 1)
        grid.addWidget(self.formats_card, 0, 2)
        grid.addWidget(self.metadata_panel, 1, 0, 1, 2)
        grid.addWidget(self.duplicates_panel, 1, 2)

        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        layout.setSpacing(SPACING.md)
        layout.addLayout(header)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.setLayout(layout)

    def update_metrics(self, metrics: SessionMetrics) -> None:
        self.total_files_card.set_value(f"{metrics.total_files:,}")
        self.total_files_card.set_breakdown(
            [
                ("Scanned files", f"{metrics.total_files:,}"),
                ("Formats found", f"{len(metrics.by_format):,}"),
            ]
        )
        self.total_size_card.set_value(_format_size(metrics.total_size_bytes))
        self.total_size_card.set_breakdown(
            [
                ("Bytes", f"{metrics.total_size_bytes:,}"),
                ("Average", _format_average_size(metrics)),
            ]
        )
        self.formats_card.set_value(f"{len(metrics.by_format):,}")
        self.formats_card.set_breakdown(_format_breakdown_rows(metrics.by_format))

    def update_metadata_health(self, health: MetadataHealth) -> None:
        self.metadata_panel.set_health(health)

    def update_duplicate_conflicts(self, groups: list[DuplicateGroup]) -> None:
        self.duplicates_panel.set_duplicate_groups(
            groups,
            self.session.preview_operations,
            duplicate_scan_complete=self.session.duplicate_scan_complete,
            preview_plan_complete=self.session.preview_plan_complete,
        )

    def update_preview_conflicts(self, operations: list[FileOperation]) -> None:
        self.duplicates_panel.set_duplicate_groups(
            self.session.duplicate_groups,
            operations,
            duplicate_scan_complete=self.session.duplicate_scan_complete,
            preview_plan_complete=self.session.preview_plan_complete,
        )

    def _update_source_path(self, source_directory: str) -> None:
        label = source_directory if source_directory else "not selected"
        self.source_path_label.setText(f"SOURCE PATH: {label}")


def _format_size(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size_bytes:,} B"


def _format_average_size(metrics: SessionMetrics) -> str:
    if metrics.total_files == 0:
        return "--"
    return _format_size(metrics.total_size_bytes // metrics.total_files)


def _format_breakdown_rows(values: dict[str, int]) -> list[tuple[str, str]]:
    if not values:
        return []
    sorted_rows = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    return [(label, f"{count:,}") for label, count in sorted_rows[:8]]


class MetadataIntegrityPanel(QWidget):
    """Dashboard panel for nullable backend metadata health metrics."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_theme_role(self, "card")
        title = QLabel("METADATA INTEGRITY")
        set_theme_role(title, "sectionLabel")
        self.gps_row = ProgressMetricRow("GPS presence")
        self.timestamp_row = ProgressMetricRow("Timestamp consistency")
        self.camera_row = ProgressMetricRow("Camera profiles")

        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        layout.setSpacing(SPACING.md)
        layout.addWidget(title)
        layout.addWidget(self.gps_row)
        layout.addWidget(self.timestamp_row)
        layout.addWidget(self.camera_row)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_health(self, health: MetadataHealth) -> None:
        self.gps_row.set_ratio(health.gps_presence)
        self.timestamp_row.set_ratio(health.timestamp_consistency)
        self.camera_row.set_ratio(health.camera_profiles)


class ProgressMetricRow(QWidget):
    """Single progress row that tolerates unknown numerator/denominator data."""

    def __init__(self, label: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = QLabel(label)
        set_theme_role(self.name, "code")
        self.percent = QLabel("--")
        set_theme_role(self.percent, "code")
        self.detail = QLabel("Awaiting backend data")
        set_theme_role(self.detail, "muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.name)
        header.addStretch(1)
        header.addWidget(self.percent)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING.xs)
        layout.addLayout(header)
        layout.addWidget(self.progress)
        layout.addWidget(self.detail)
        self.setLayout(layout)

    def set_ratio(self, ratio: MetadataRatio) -> None:
        if ratio.available is None or ratio.total is None or ratio.total <= 0:
            self.percent.setText("--")
            self.detail.setText("Awaiting backend data")
            self.progress.setValue(0)
            return

        available = max(0, min(ratio.available, ratio.total))
        percent = round((available / ratio.total) * 100)
        self.percent.setText(f"{percent}%")
        self.detail.setText(f"{available:,} of {ratio.total:,} files")
        self.progress.setValue(percent)


class DuplicateConflictPanel(QWidget):
    """Dashboard panel for duplicate groups and planned conflict signals."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_theme_role(self, "card")
        title = QLabel("DUPLICATES / CONFLICTS")
        set_theme_role(title, "sectionLabel")
        self.total_label = QLabel("--")
        set_theme_role(self.total_label, "metric")
        self.groups_row = _MiniValueRow("Duplicate groups", "--")
        self.files_row = _MiniValueRow("Files in groups", "--")
        self.conflicts_row = _MiniValueRow("Planned conflicts", "--")
        self.preview_layout = QHBoxLayout()
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(SPACING.sm)

        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        layout.setSpacing(SPACING.md)
        layout.addWidget(title)
        layout.addWidget(self.total_label)
        layout.addWidget(self.groups_row)
        layout.addWidget(self.files_row)
        layout.addWidget(self.conflicts_row)
        layout.addLayout(self.preview_layout)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_duplicate_groups(
        self,
        groups: list[DuplicateGroup],
        operations: list[FileOperation],
        *,
        duplicate_scan_complete: bool,
        preview_plan_complete: bool,
    ) -> None:
        duplicate_files = sum(1 + len(group.duplicates) for group in groups)
        operation_conflicts = sum(
            1 for operation in operations if _operation_has_conflict(operation)
        )
        total_conflicts = len(groups) + operation_conflicts

        has_conflict_data = duplicate_scan_complete or preview_plan_complete
        self.total_label.setText(f"{total_conflicts:,}" if has_conflict_data else "--")
        self.groups_row.set_value(f"{len(groups):,}" if duplicate_scan_complete else "--")
        self.files_row.set_value(f"{duplicate_files:,}" if duplicate_scan_complete else "--")
        self.conflicts_row.set_value(
            f"{operation_conflicts:,}" if preview_plan_complete else "--"
        )
        self._set_previews(_duplicate_preview_paths(groups))

    def _set_previews(self, paths: list[Path]) -> None:
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        preview_paths = paths[:3]
        if not preview_paths:
            self.preview_layout.addWidget(_PreviewPlaceholder("No previews"))
            return

        for path in preview_paths:
            self.preview_layout.addWidget(_PreviewPlaceholder(path.name, path=path))
        self.preview_layout.addStretch(1)


class _MiniValueRow(QWidget):
    def __init__(self, label: str, value: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        name = QLabel(label)
        set_theme_role(name, "code")
        self.value = QLabel(value)
        set_theme_role(self.value, "code")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(name)
        layout.addStretch(1)
        layout.addWidget(self.value)
        self.setLayout(layout)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


class _PreviewPlaceholder(QLabel):
    def __init__(
        self,
        text: str,
        *,
        path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedSize(72, 48)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        set_theme_role(self, "badge")
        if path is not None:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self.setPixmap(
                    pixmap.scaled(
                        self.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.setToolTip(str(path))
                return
        self.setText(text)
        if path is not None:
            self.setToolTip(str(path))


def _operation_has_conflict(operation: FileOperation) -> bool:
    if "REVIEW_CONFLICT" in operation.review_flags:
        return True
    return (
        operation.date_reconciliation is not None
        and operation.date_reconciliation.conflict
    )


def _duplicate_preview_paths(groups: list[DuplicateGroup]) -> list[Path]:
    paths: list[Path] = []
    for group in groups:
        paths.append(group.original)
        paths.extend(group.duplicates)
        if len(paths) >= 3:
            break
    return paths
