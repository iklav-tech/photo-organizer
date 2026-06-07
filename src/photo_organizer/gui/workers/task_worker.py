"""Reusable worker primitive for GUI background tasks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from PySide6.QtCore import QObject, Signal, Slot

from photo_organizer.gui.session import LogEvent, TaskProgress


ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class TaskReporter:
    """Thread-safe signal facade passed to background GUI tasks."""

    progress_signal: Signal
    log_signal: Signal

    def progress(
        self,
        label: str,
        *,
        current: int = 0,
        total: int = 0,
        detail: str = "",
    ) -> None:
        self.progress_signal.emit(
            TaskProgress(label=label, current=current, total=total, detail=detail)
        )

    def log(self, message: str, *, level: str = "INFO", source: str = "task") -> None:
        self.log_signal.emit(LogEvent(message=message, level=level, source=source))


class TaskWorker(QObject, Generic[ResultT]):
    """Run a callable and report either a result or an exception."""

    progress = Signal(object)
    log_event = Signal(object)
    finished = Signal(object)
    failed = Signal(Exception)

    def __init__(self, task: Callable[[TaskReporter], ResultT]) -> None:
        super().__init__()
        self._task = task

    @Slot()
    def run(self) -> None:
        try:
            reporter = TaskReporter(
                progress_signal=self.progress,
                log_signal=self.log_event,
            )
            self.finished.emit(self._task(reporter))
        except Exception as exc:  # pragma: no cover - Qt signal handoff
            self.failed.emit(exc)
