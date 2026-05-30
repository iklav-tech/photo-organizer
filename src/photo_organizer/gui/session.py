"""Shared GUI session state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from photo_organizer.executor import FileOperation
from photo_organizer.hashing import DuplicateGroup


@dataclass(frozen=True)
class SessionMetrics:
    """Computed values shown by the GUI and reused by previews/logs."""

    total_files: int = 0
    total_size_bytes: int = 0
    by_extension: dict[str, int] = field(default_factory=dict)
    by_format: dict[str, int] = field(default_factory=dict)


class SessionState(QObject):
    """Mutable session state shared by the main window and pages."""

    source_directory_changed = Signal(str)
    metrics_changed = Signal(object)
    log_message_added = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.source_directory = ""
        self.scanned_files: list[Path] = []
        self.duplicate_groups: list[DuplicateGroup] = []
        self.preview_operations: list[FileOperation] = []
        self.metrics = SessionMetrics()
        self.logs: list[str] = []

    def set_source_directory(self, source_directory: str) -> None:
        normalized = str(Path(source_directory).expanduser())
        if normalized == self.source_directory:
            return
        self.source_directory = normalized
        self.scanned_files = []
        self.duplicate_groups = []
        self.preview_operations = []
        self.metrics = SessionMetrics()
        self.source_directory_changed.emit(normalized)
        self.metrics_changed.emit(self.metrics)

    def set_scan_result(
        self,
        files: list[Path],
        *,
        total_size_bytes: int = 0,
        by_extension: dict[str, int] | None = None,
        by_format: dict[str, int] | None = None,
    ) -> None:
        self.scanned_files = files
        self.metrics = SessionMetrics(
            total_files=len(files),
            total_size_bytes=total_size_bytes,
            by_extension=by_extension or {},
            by_format=by_format or {},
        )
        self.metrics_changed.emit(self.metrics)

    def set_duplicate_groups(self, groups: list[DuplicateGroup]) -> None:
        self.duplicate_groups = groups

    def set_preview_operations(self, operations: list[FileOperation]) -> None:
        self.preview_operations = operations

    def add_log(self, message: str) -> None:
        self.logs.append(message)
        self.log_message_added.emit(message)
