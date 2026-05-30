from __future__ import annotations

import sys
import types
from pathlib import Path

from photo_organizer.gui import app as gui_app
from photo_organizer.gui import windowing


def test_gui_run_applies_startup_geometry(monkeypatch) -> None:
    calls: list[str] = []

    pyside6_module = types.ModuleType("PySide6")
    qtwidgets_module = types.ModuleType("PySide6.QtWidgets")

    class FakeApplication:
        def __init__(self, argv):
            calls.append(f"app:{argv}")

        @staticmethod
        def instance():
            return None

        def exec(self):
            calls.append("exec")
            return 0

    class FakeAdapter:
        pass

    class FakeMainWindow:
        def __init__(self, *, adapter):
            assert isinstance(adapter, FakeAdapter)
            calls.append("window")

    def fake_apply_app_theme(qt_app):
        assert isinstance(qt_app, FakeApplication)
        calls.append("theme")

    def fake_apply_startup_geometry(window):
        assert isinstance(window, FakeMainWindow)
        calls.append("startupGeometry")

    qtwidgets_module.QApplication = FakeApplication

    organizer_module = types.ModuleType("photo_organizer.gui.adapters.organizer")
    organizer_module.OrganizerAdapter = FakeAdapter
    main_window_module = types.ModuleType("photo_organizer.gui.main_window")
    main_window_module.MainWindow = FakeMainWindow
    theme_module = types.ModuleType("photo_organizer.gui.theme")
    theme_module.apply_app_theme = fake_apply_app_theme
    windowing_module = types.ModuleType("photo_organizer.gui.windowing")
    windowing_module.apply_startup_geometry = fake_apply_startup_geometry

    monkeypatch.setitem(sys.modules, "PySide6", pyside6_module)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets_module)
    monkeypatch.setitem(
        sys.modules,
        "photo_organizer.gui.adapters.organizer",
        organizer_module,
    )
    monkeypatch.setitem(sys.modules, "photo_organizer.gui.main_window", main_window_module)
    monkeypatch.setitem(sys.modules, "photo_organizer.gui.theme", theme_module)
    monkeypatch.setitem(sys.modules, "photo_organizer.gui.windowing", windowing_module)

    assert gui_app.run(["--example"]) == 0

    assert calls == ["app:['--example']", "theme", "window", "startupGeometry", "exec"]


def test_get_startup_screen_prefers_screen_under_cursor(monkeypatch) -> None:
    cursor_screen = object()
    primary_screen = object()

    class FakeCursor:
        @staticmethod
        def pos():
            return "cursor-position"

    class FakeGuiApplication:
        @staticmethod
        def screenAt(position):
            assert position == "cursor-position"
            return cursor_screen

        @staticmethod
        def primaryScreen():
            return primary_screen

        @staticmethod
        def screens():
            return []

    monkeypatch.setattr(windowing, "QCursor", FakeCursor)
    monkeypatch.setattr(windowing, "QGuiApplication", FakeGuiApplication)

    assert windowing.get_startup_screen() is cursor_screen


def test_get_startup_screen_falls_back_to_primary_screen(monkeypatch) -> None:
    primary_screen = object()

    class FakeCursor:
        @staticmethod
        def pos():
            return "cursor-position"

    class FakeGuiApplication:
        @staticmethod
        def screenAt(position):
            assert position == "cursor-position"
            return None

        @staticmethod
        def primaryScreen():
            return primary_screen

        @staticmethod
        def screens():
            return []

    monkeypatch.setattr(windowing, "QCursor", FakeCursor)
    monkeypatch.setattr(windowing, "QGuiApplication", FakeGuiApplication)

    assert windowing.get_startup_screen() is primary_screen


def test_apply_startup_geometry_uses_available_geometry(monkeypatch) -> None:
    calls: list[object] = []

    class FakeGeometry:
        def topLeft(self):
            return "top-left"

    class FakeScreen:
        def availableGeometry(self):
            return FakeGeometry()

    class FakeWindow:
        def setGeometry(self, geometry):
            calls.append(("setGeometry", geometry.__class__.__name__))

        def move(self, position):
            calls.append(("move", position))

        def showMaximized(self):
            calls.append("showMaximized")

    monkeypatch.setattr(windowing, "get_startup_screen", lambda: FakeScreen())

    windowing.apply_startup_geometry(FakeWindow())

    assert calls == [
        ("setGeometry", "FakeGeometry"),
        ("move", "top-left"),
        "showMaximized",
    ]


def test_main_window_wraps_pages_in_scroll_areas() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QScrollArea

    from photo_organizer.gui.adapters.organizer import OrganizerAdapter
    from photo_organizer.gui.main_window import MainWindow
    from photo_organizer.gui.theme import apply_app_theme

    app = QApplication.instance() or QApplication([])
    apply_app_theme(app)

    window = MainWindow(adapter=OrganizerAdapter())

    assert window.stack.count() == 4
    assert all(
        isinstance(window.stack.widget(index), QScrollArea)
        for index in range(window.stack.count())
    )


def test_main_window_select_source_directory_updates_session_and_scans(monkeypatch, tmp_path) -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from photo_organizer.gui.main_window import MainWindow
    from photo_organizer.gui.session import SessionState
    from photo_organizer.gui.theme import apply_app_theme

    app = QApplication.instance() or QApplication([])
    apply_app_theme(app)

    selected_source = tmp_path / "source"
    selected_source.mkdir()
    scanned_file = selected_source / "photo.jpg"
    scanned_file.write_bytes(b"fake")

    class FakeAdapter:
        def __init__(self):
            self.scanned_sources = []

        def scan(self, source):
            self.scanned_sources.append(source)
            return [Path(source) / "photo.jpg"]

    adapter = FakeAdapter()
    session = SessionState()
    monkeypatch.setattr(
        "photo_organizer.gui.main_window.QFileDialog.getExistingDirectory",
        lambda *args: str(selected_source),
    )

    window = MainWindow(adapter=adapter, session=session)
    window.select_source_directory()

    assert session.source_directory == str(selected_source)
    assert session.scanned_files == [scanned_file]
    assert session.metrics.total_files == 1
    assert session.metrics.by_extension == {".jpg": 1}
    assert adapter.scanned_sources == [str(selected_source)]
    assert window.source_path_label.text() == f"SOURCE PATH: {selected_source}"
    assert window.organize_page.source_picker.text() == str(selected_source)
