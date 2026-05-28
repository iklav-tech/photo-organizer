"""Placeholder pages for navigation skeleton."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from photo_organizer.gui.theme import set_theme_role


class PlaceholderPage(QWidget):
    """Simple page used to reserve navigation targets."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_theme_role(self, "page")
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_theme_role(label, "headline")

        layout = QVBoxLayout()
        layout.addWidget(label, 1)
        self.setLayout(layout)
