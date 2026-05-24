"""Reusable worker primitive for GUI background tasks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from PySide6.QtCore import QObject, Signal, Slot


ResultT = TypeVar("ResultT")


class TaskWorker(QObject, Generic[ResultT]):
    """Run a callable and report either a result or an exception."""

    finished = Signal(object)
    failed = Signal(Exception)

    def __init__(self, task: Callable[[], ResultT]) -> None:
        super().__init__()
        self._task = task

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self._task())
        except Exception as exc:  # pragma: no cover - Qt signal handoff
            self.failed.emit(exc)
