"""Window placement helpers for the desktop GUI."""

from __future__ import annotations

from PySide6.QtGui import QCursor, QGuiApplication, QScreen
from PySide6.QtWidgets import QMainWindow


def get_startup_screen() -> QScreen | None:
    """Return the screen where the GUI should open.

    Preference is the monitor under the cursor, then the primary screen, then
    the first screen known to Qt. Returning ``None`` is allowed in unusual
    headless or partially initialized environments.
    """
    cursor_screen = QGuiApplication.screenAt(QCursor.pos())
    if cursor_screen is not None:
        return cursor_screen

    primary_screen = QGuiApplication.primaryScreen()
    if primary_screen is not None:
        return primary_screen

    screens = QGuiApplication.screens()
    return screens[0] if screens else None


def apply_startup_geometry(window: QMainWindow) -> None:
    """Place and maximize a window within one monitor's available geometry."""
    screen = get_startup_screen()
    if screen is not None:
        available_geometry = screen.availableGeometry()
        window.setGeometry(available_geometry)
        window.move(available_geometry.topLeft())

    window.showMaximized()
