"""Placeholder pages for navigation skeleton."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """Simple page used to reserve navigation targets."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(label, 1)
        self.setLayout(layout)
