"""Main GUI window and page navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from photo_organizer import __app_name__
from photo_organizer.gui.adapters import OrganizerAdapter
from photo_organizer.gui.pages import OrganizePage, PlaceholderPage
from photo_organizer.gui.session import SessionMetrics, SessionState
from photo_organizer.gui.theme import SPACING, set_active, set_theme_role
from photo_organizer.gui.widgets import create_scrollable_page


PAGE_DASHBOARD = 0
PAGE_ORGANIZE = 1
PAGE_AUDIT = 2
PAGE_SETTINGS = 3


class MainWindow(QMainWindow):
    """Top-level window with stacked page navigation."""

    def __init__(
        self,
        adapter: OrganizerAdapter,
        session: SessionState | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self.session = session or SessionState(self)
        self._nav_buttons: list[QPushButton] = []
        self.setWindowTitle(__app_name__)
        self.resize(1280, 780)
        self._build_ui()

    def _build_ui(self) -> None:
        self.stack = QStackedWidget()
        self.dashboard_page = PlaceholderPage("Dashboard")
        self.organize_page = OrganizePage(adapter=self._adapter, session=self.session)
        self.audit_page = PlaceholderPage("Audit")
        self.settings_page = PlaceholderPage("Settings")

        self.stack.addWidget(create_scrollable_page(self.dashboard_page))
        self.stack.addWidget(create_scrollable_page(self.organize_page))
        self.stack.addWidget(create_scrollable_page(self.audit_page))
        self.stack.addWidget(create_scrollable_page(self.settings_page))

        shell = QWidget()
        set_theme_role(shell, "appShell")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_main_region(), 1)

        shell.setLayout(layout)
        self.setCentralWidget(shell)
        self.show_page(PAGE_DASHBOARD)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(SPACING.sidebar_width)
        set_theme_role(sidebar, "sidebar")

        brand = QLabel("PHOTOMASTER")
        set_theme_role(brand, "brand")
        version = QLabel("V1.0.4 PRO")
        set_theme_role(version, "metadata")

        brand_layout = QVBoxLayout()
        brand_layout.setContentsMargins(SPACING.md, SPACING.lg, SPACING.md, SPACING.xl)
        brand_layout.setSpacing(SPACING.xs)
        brand_layout.addWidget(brand)
        brand_layout.addWidget(version)

        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(SPACING.xs)
        nav_layout.addWidget(self._make_nav_button("Dashboard", PAGE_DASHBOARD))
        nav_layout.addWidget(self._make_nav_button("Organize", PAGE_ORGANIZE))
        nav_layout.addWidget(self._make_nav_button("Audit", PAGE_AUDIT))
        nav_layout.addWidget(self._make_nav_button("Settings", PAGE_SETTINGS))

        select_folder = QPushButton("Select Folder")
        set_theme_role(select_folder, "secondaryButton")
        select_folder.clicked.connect(self.select_source_directory)

        support = QLabel("Support")
        set_theme_role(support, "code")
        logs = QLabel("Logs")
        set_theme_role(logs, "code")

        user_badge = QLabel("Admin Mode\nid: 0822-1X")
        set_theme_role(user_badge, "code")

        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(SPACING.md, 0, SPACING.md, SPACING.lg)
        bottom_layout.setSpacing(SPACING.md)
        bottom_layout.addWidget(select_folder)
        bottom_layout.addWidget(support)
        bottom_layout.addWidget(logs)
        bottom_layout.addSpacing(SPACING.md)
        bottom_layout.addWidget(user_badge)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(brand_layout)
        layout.addLayout(nav_layout)
        layout.addStretch(1)
        layout.addLayout(bottom_layout)
        sidebar.setLayout(layout)
        return sidebar

    def _build_main_region(self) -> QWidget:
        region = QWidget()
        set_theme_role(region, "page")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_topbar())
        layout.addWidget(self.stack, 1)
        layout.addWidget(self._build_footer())
        region.setLayout(layout)
        return region

    def _build_topbar(self) -> QWidget:
        topbar = QWidget()
        topbar.setFixedHeight(SPACING.topbar_height)
        set_theme_role(topbar, "topbar")

        title = QLabel("Photo Organizer")
        set_theme_role(title, "headline")
        self.source_path_label = QLabel("SOURCE PATH: not selected")
        self.source_path_label.setTextInteractionFlags(
            self.source_path_label.textInteractionFlags()
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        set_theme_role(self.source_path_label, "metadata")
        self.source_metrics_label = QLabel("SCAN: -- files")
        set_theme_role(self.source_metrics_label, "code")
        execute = QPushButton("Execute Move")
        set_theme_role(execute, "primaryButton")

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(SPACING.xs)
        title_layout.addWidget(title)
        title_layout.addWidget(self.source_path_label)

        layout = QHBoxLayout()
        layout.setContentsMargins(SPACING.lg, 0, SPACING.lg, 0)
        layout.setSpacing(SPACING.lg)
        layout.addLayout(title_layout)
        layout.addWidget(self.source_metrics_label)
        layout.addStretch(1)
        layout.addWidget(execute)
        topbar.setLayout(layout)
        self.session.source_directory_changed.connect(self._update_source_path)
        self.session.metrics_changed.connect(self._update_source_metrics)
        return topbar

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(SPACING.footer_height)
        set_theme_role(footer, "footer")

        engine = QLabel("PHOTOMASTER.SYS   System Engine v1.0.4 - Ready")
        set_theme_role(engine, "code")
        actions = QLabel("Terminal Output     Process Monitor     Clear Cache     9.2 ms")
        set_theme_role(actions, "code")

        layout = QHBoxLayout()
        layout.setContentsMargins(SPACING.md, 0, SPACING.md, 0)
        layout.addWidget(engine)
        layout.addStretch(1)
        layout.addWidget(actions)
        footer.setLayout(layout)
        return footer

    def _make_nav_button(self, text: str, index: int) -> QPushButton:
        button = QPushButton(text)
        set_theme_role(button, "navButton")
        button.clicked.connect(lambda: self.show_page(index))
        self._nav_buttons.append(button)
        return button

    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self._nav_buttons):
            set_active(button, button_index == index)

    def select_source_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta de origem",
            self.session.source_directory,
        )
        if not directory:
            return
        self.session.set_source_directory(directory)
        self.show_page(PAGE_ORGANIZE)
        self.organize_page.scan_source()

    def _update_source_path(self, source_directory: str) -> None:
        self.source_path_label.setText(f"SOURCE PATH: {source_directory}")

    def _update_source_metrics(self, metrics: SessionMetrics) -> None:
        self.source_metrics_label.setText(f"SCAN: {metrics.total_files:,} files")
