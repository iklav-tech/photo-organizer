"""Main GUI window and page navigation."""

from __future__ import annotations

from PySide6.QtWidgets import (
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
from photo_organizer.gui.theme import SPACING, set_active, set_theme_role


class MainWindow(QMainWindow):
    """Top-level window with stacked page navigation."""

    def __init__(
        self,
        adapter: OrganizerAdapter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._nav_buttons: list[QPushButton] = []
        self.setWindowTitle(__app_name__)
        self.resize(1280, 780)
        self._build_ui()

    def _build_ui(self) -> None:
        self.stack = QStackedWidget()
        self.organize_page = OrganizePage(adapter=self._adapter)
        self.scan_page = PlaceholderPage("Organize")
        self.dedupe_page = PlaceholderPage("Audit")

        self.stack.addWidget(self.organize_page)
        self.stack.addWidget(self.scan_page)
        self.stack.addWidget(self.dedupe_page)

        shell = QWidget()
        set_theme_role(shell, "appShell")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_main_region(), 1)

        shell.setLayout(layout)
        self.setCentralWidget(shell)
        self.show_page(0)

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
        nav_layout.addWidget(self._make_nav_button("Dashboard", 0))
        nav_layout.addWidget(self._make_nav_button("Organize", 1))
        nav_layout.addWidget(self._make_nav_button("Audit", 2))

        select_folder = QPushButton("Select Folder")
        set_theme_role(select_folder, "secondaryButton")
        select_folder.clicked.connect(self.organize_page.source_picker.select_directory)

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
        workflow = QLabel("Import   Export   Batch Edit")
        set_theme_role(workflow, "code")
        execute = QPushButton("Execute Move")
        set_theme_role(execute, "primaryButton")
        execute.clicked.connect(self.organize_page.execute_plan)

        layout = QHBoxLayout()
        layout.setContentsMargins(SPACING.lg, 0, SPACING.lg, 0)
        layout.setSpacing(SPACING.lg)
        layout.addWidget(title)
        layout.addWidget(workflow)
        layout.addStretch(1)
        layout.addWidget(execute)
        topbar.setLayout(layout)
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
