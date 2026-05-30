"""Reusable dashboard metric card widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from photo_organizer.gui.theme import SPACING, set_theme_role


class MetricCard(QWidget):
    """Card with a title, prominent value and secondary breakdown rows."""

    def __init__(self, title: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_theme_role(self, "card")
        self.title_label = QLabel(title)
        set_theme_role(self.title_label, "sectionLabel")
        self.value_label = QLabel("--")
        set_theme_role(self.value_label, "metric")
        self.breakdown_layout = QVBoxLayout()
        self.breakdown_layout.setContentsMargins(0, 0, 0, 0)
        self.breakdown_layout.setSpacing(SPACING.xs)

        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        layout.setSpacing(SPACING.md)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addLayout(self.breakdown_layout)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_breakdown(self, rows: list[tuple[str, str]]) -> None:
        while self.breakdown_layout.count():
            item = self.breakdown_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not rows:
            self.breakdown_layout.addWidget(self._row("No data", "--"))
            return
        for label, value in rows:
            self.breakdown_layout.addWidget(self._row(label, value))

    def _row(self, label: str, value: str) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(SPACING.sm)
        name = QLabel(label)
        name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        set_theme_role(name, "code")
        amount = QLabel(value)
        amount.setAlignment(Qt.AlignmentFlag.AlignRight)
        set_theme_role(amount, "code")
        row_layout.addWidget(name)
        row_layout.addStretch(1)
        row_layout.addWidget(amount)
        row.setLayout(row_layout)
        return row
