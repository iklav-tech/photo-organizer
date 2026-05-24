"""Main GUI window and page navigation."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from photo_organizer import __app_name__
from photo_organizer.gui.adapters import OrganizerAdapter
from photo_organizer.gui.pages import OrganizePage, PlaceholderPage


class MainWindow(QMainWindow):
    """Top-level window with stacked page navigation."""

    def __init__(
        self,
        adapter: OrganizerAdapter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self.setWindowTitle(__app_name__)
        self.resize(980, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        self.stack = QStackedWidget()
        self.organize_page = OrganizePage(adapter=self._adapter)
        self.scan_page = PlaceholderPage("Scan")
        self.dedupe_page = PlaceholderPage("Dedupe")

        self.stack.addWidget(self.organize_page)
        self.stack.addWidget(self.scan_page)
        self.stack.addWidget(self.dedupe_page)

        organize_button = QPushButton("Organizar")
        organize_button.clicked.connect(lambda: self.show_page(0))
        scan_button = QPushButton("Scan")
        scan_button.clicked.connect(lambda: self.show_page(1))
        dedupe_button = QPushButton("Dedupe")
        dedupe_button.clicked.connect(lambda: self.show_page(2))

        navigation = QHBoxLayout()
        navigation.addWidget(organize_button)
        navigation.addWidget(scan_button)
        navigation.addWidget(dedupe_button)
        navigation.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(navigation)
        layout.addWidget(self.stack, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
