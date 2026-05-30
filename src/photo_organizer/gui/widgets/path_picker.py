"""Directory picker widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from photo_organizer.gui.theme import set_theme_role


class PathPicker(QWidget):
    """A line edit plus a directory selection button."""

    directory_selected = Signal(str)

    def __init__(self, *, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._caption = caption
        self.line_edit = QLineEdit()
        self.button = QPushButton("Selecionar")
        set_theme_role(self.button, "secondaryButton")
        self.button.clicked.connect(self.select_directory)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def text(self) -> str:
        return self.line_edit.text().strip()

    def set_text(self, value: str) -> None:
        self.line_edit.setText(value)

    def select_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, self._caption)
        if directory:
            self.set_text(directory)
            self.directory_selected.emit(directory)
