"""Visual theme helpers for the PySide6 GUI."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication


def apply_app_theme(app: QApplication) -> None:
    """Apply the initial application style sheet."""
    app.setStyleSheet(
        """
        QWidget {
            font-size: 13px;
        }
        QMainWindow {
            background: #f6f7f9;
        }
        QPushButton {
            padding: 6px 10px;
        }
        QLineEdit, QComboBox, QPlainTextEdit {
            background: #ffffff;
            border: 1px solid #c9ced6;
            border-radius: 4px;
            padding: 5px;
        }
        QPlainTextEdit {
            font-family: monospace;
        }
        """
    )
