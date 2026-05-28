"""GUI application bootstrap."""

from __future__ import annotations


class GuiDependencyError(RuntimeError):
    """Raised when the optional GUI dependency is unavailable."""


GUI_INSTALL_MESSAGE = (
    "A interface grafica requer PySide6. Instale a dependencia de GUI com:\n"
    "  python -m pip install 'photo-organizer[gui]'\n"
    "ou, em uma instalacao editavel/local:\n"
    "  python -m pip install PySide6"
)


def _ensure_pyside6_available() -> None:
    try:
        import PySide6  # noqa: F401, PLC0415
    except ModuleNotFoundError as exc:
        missing_name = exc.name or ""
        if missing_name == "PySide6" or missing_name.startswith("PySide6."):
            raise GuiDependencyError(GUI_INSTALL_MESSAGE) from exc
        raise


def run(argv: list[str] | None = None) -> int:
    """Run the optional Qt application."""
    _ensure_pyside6_available()

    from PySide6.QtWidgets import QApplication  # noqa: PLC0415

    from photo_organizer.gui.adapters.organizer import OrganizerAdapter  # noqa: PLC0415
    from photo_organizer.gui.main_window import MainWindow  # noqa: PLC0415
    from photo_organizer.gui.theme import apply_app_theme  # noqa: PLC0415
    from photo_organizer.gui.windowing import apply_startup_geometry  # noqa: PLC0415

    app = QApplication.instance() or QApplication(argv or [])
    apply_app_theme(app)

    window = MainWindow(adapter=OrganizerAdapter())
    apply_startup_geometry(window)
    return app.exec()
