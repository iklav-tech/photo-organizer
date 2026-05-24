"""Optional PySide6 GUI package."""

from __future__ import annotations

from photo_organizer.gui.app import GUI_INSTALL_MESSAGE, GuiDependencyError


def run(argv: list[str] | None = None) -> int:
    """Start the GUI application.

    Importing the heavy Qt window tree is deferred until this function runs.
    """
    from photo_organizer.gui.app import run as run_app  # noqa: PLC0415

    return run_app(argv)


__all__ = ["GUI_INSTALL_MESSAGE", "GuiDependencyError", "run"]
