"""Shared GUI session state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

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


@dataclass(frozen=True)
class MetadataRatio:
    """Nullable ratio used by dashboard metadata health widgets."""

    available: int | None = None
    total: int | None = None


@dataclass(frozen=True)
class MetadataHealth:
    """Best-effort metadata integrity summary for scanned files."""

    gps_presence: MetadataRatio = field(default_factory=MetadataRatio)
    timestamp_consistency: MetadataRatio = field(default_factory=MetadataRatio)
    camera_profiles: MetadataRatio = field(default_factory=MetadataRatio)


LogLevel = Literal["INFO", "WARNING", "ERROR"]


@dataclass(frozen=True)
class LogEvent:
    """Structured GUI log line emitted by user actions or backend logging."""

    message: str
    level: LogLevel = "INFO"
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "gui"


@dataclass(frozen=True)
class TaskProgress:
    """Progress event shape shared by current and future async GUI tasks."""

    label: str
    current: int = 0
    total: int = 0
    detail: str = ""

    @property
    def percent(self) -> int | None:
        if self.total <= 0:
            return None
        return round((max(0, min(self.current, self.total)) / self.total) * 100)


class SessionState(QObject):
    """Mutable session state shared by the main window and pages."""

    source_directory_changed = Signal(str)
    metrics_changed = Signal(object)
    metadata_health_changed = Signal(object)
    duplicate_groups_changed = Signal(object)
    preview_operations_changed = Signal(object)
    log_message_added = Signal(str)
    log_event_added = Signal(object)
    task_progress_changed = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.source_directory = ""
        self.scanned_files: list[Path] = []
        self.duplicate_groups: list[DuplicateGroup] = []
        self.duplicate_scan_complete = False
        self.preview_operations: list[FileOperation] = []
        self.preview_plan_complete = False
        self.metrics = SessionMetrics()
        self.metadata_health = MetadataHealth()
        self.logs: list[LogEvent] = []

    def set_source_directory(self, source_directory: str) -> None:
        normalized = str(Path(source_directory).expanduser())
        if normalized == self.source_directory:
            return
        self.source_directory = normalized
        self.scanned_files = []
        self.duplicate_groups = []
        self.duplicate_scan_complete = False
        self.preview_operations = []
        self.preview_plan_complete = False
        self.metrics = SessionMetrics()
        self.metadata_health = MetadataHealth()
        self.source_directory_changed.emit(normalized)
        self.metrics_changed.emit(self.metrics)
        self.metadata_health_changed.emit(self.metadata_health)
        self.duplicate_groups_changed.emit(self.duplicate_groups)
        self.preview_operations_changed.emit(self.preview_operations)

    def set_scan_result(
        self,
        files: list[Path],
        *,
        total_size_bytes: int = 0,
        by_extension: dict[str, int] | None = None,
        by_format: dict[str, int] | None = None,
        metadata_health: MetadataHealth | None = None,
    ) -> None:
        self.scanned_files = files
        self.metrics = SessionMetrics(
            total_files=len(files),
            total_size_bytes=total_size_bytes,
            by_extension=by_extension or {},
            by_format=by_format or {},
        )
        self.metadata_health = metadata_health or MetadataHealth()
        self.metrics_changed.emit(self.metrics)
        self.metadata_health_changed.emit(self.metadata_health)

    def set_duplicate_groups(self, groups: list[DuplicateGroup]) -> None:
        self.duplicate_groups = groups
        self.duplicate_scan_complete = True
        self.duplicate_groups_changed.emit(groups)

    def set_preview_operations(self, operations: list[FileOperation]) -> None:
        self.preview_operations = operations
        self.preview_plan_complete = True
        self.preview_operations_changed.emit(operations)

    def add_log(
        self,
        message: str,
        *,
        level: LogLevel = "INFO",
        source: str = "gui",
    ) -> None:
        self.add_log_event(LogEvent(message=message, level=level, source=source))

    def add_log_event(self, event: LogEvent) -> None:
        self.logs.append(event)
        self.log_event_added.emit(event)
        self.log_message_added.emit(event.message)

    def report_progress(self, progress: TaskProgress) -> None:
        self.task_progress_changed.emit(progress)
