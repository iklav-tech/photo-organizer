"""Dashboard page with scan session metrics."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from photo_organizer.gui.session import SessionMetrics, SessionState
from photo_organizer.gui.theme import SPACING, set_theme_role
from photo_organizer.gui.widgets import MetricCard


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
        self._update_source_path(self.session.source_directory)
        self.update_metrics(self.session.metrics)

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

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING.md)
        grid.setVerticalSpacing(SPACING.md)
        grid.addWidget(self.total_files_card, 0, 0)
        grid.addWidget(self.total_size_card, 0, 1)
        grid.addWidget(self.formats_card, 0, 2)

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
