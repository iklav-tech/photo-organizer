from __future__ import annotations

import sys
import types
from types import SimpleNamespace
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

    from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

    from photo_organizer.gui.adapters.organizer import OrganizerAdapter
    from photo_organizer.gui.main_window import MainWindow
    from photo_organizer.gui.theme import apply_app_theme

    app = QApplication.instance() or QApplication([])
    apply_app_theme(app)

    window = MainWindow(adapter=OrganizerAdapter())

    assert window.stack.count() == 4
    assert window.windowTitle() == "photo-organizer"
    assert all(
        isinstance(window.stack.widget(index), QScrollArea)
        for index in range(window.stack.count())
    )
    assert any(label.text() == "PHOTO ORGANIZER" for label in window.findChildren(QLabel))
    assert any(label.text() == "v1.1.0" for label in window.findChildren(QLabel))


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

        def scan_metrics(self, files):
            return SimpleNamespace(
                total_size_bytes=sum(path.stat().st_size for path in files),
                by_extension={".jpg": len(files)},
                by_format={"JPEG": len(files)},
            )

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
    assert window.dashboard_page.total_files_card.value_label.text() == "1"
    assert window.dashboard_page.total_size_card.value_label.text() == "4 B"
    assert window.dashboard_page.formats_card.value_label.text() == "1"


def test_dashboard_shows_metadata_health_and_duplicate_summary(tmp_path) -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from photo_organizer.gui.pages.dashboard_page import DashboardPage
    from photo_organizer.gui.session import (
        MetadataHealth,
        MetadataRatio,
        SessionState,
    )
    from photo_organizer.gui.theme import apply_app_theme
    from photo_organizer.hashing import DuplicateGroup

    app = QApplication.instance() or QApplication([])
    apply_app_theme(app)

    original = tmp_path / "a.jpg"
    duplicate = tmp_path / "b.jpg"
    original.write_bytes(b"same")
    duplicate.write_bytes(b"same")

    session = SessionState()
    dashboard = DashboardPage(session=session)

    assert dashboard.metadata_panel.gps_row.percent.text() == "--"
    assert dashboard.duplicates_panel.total_label.text() == "--"

    session.set_scan_result(
        [original, duplicate],
        total_size_bytes=8,
        by_extension={".jpg": 2},
        by_format={"JPEG": 2},
        metadata_health=MetadataHealth(
            gps_presence=MetadataRatio(1, 2),
            timestamp_consistency=MetadataRatio(2, 2),
            camera_profiles=MetadataRatio(0, 2),
        ),
    )
    session.set_duplicate_groups(
        [
            DuplicateGroup(
                content_hash="hash",
                original=original,
                duplicates=(duplicate,),
            )
        ]
    )

    assert dashboard.metadata_panel.gps_row.percent.text() == "50%"
    assert dashboard.metadata_panel.timestamp_row.percent.text() == "100%"
    assert dashboard.metadata_panel.camera_row.percent.text() == "0%"
    assert dashboard.duplicates_panel.total_label.text() == "1"
    assert dashboard.duplicates_panel.groups_row.value.text() == "1"
    assert dashboard.duplicates_panel.files_row.value.text() == "2"
