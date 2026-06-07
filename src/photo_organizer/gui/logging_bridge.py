"""Bridge Python logging records into the Qt GUI session."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Protocol

from photo_organizer.gui.session import LogEvent, SessionState


class LogEventQueue(Protocol):
    """Queue shape shared by local and multiprocessing queues."""

    def put(self, item: LogEvent) -> object: ...

    def get_nowait(self) -> LogEvent: ...


class FileLogEventWriter:
    """Queue-like writer backed by an append-only JSONL spool file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def put(self, item: LogEvent) -> object:
        payload = {
            "message": item.message,
            "level": item.level,
            "timestamp": item.timestamp.isoformat(),
            "source": item.source,
        }
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True))
            file.write("\n")
        return None


class FileLogEventReader:
    """Queue-like non-blocking reader backed by a JSONL spool file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._offset = 0

    def get_nowait(self) -> LogEvent:
        if not self._path.exists():
            raise Empty
        with self._path.open("r", encoding="utf-8") as file:
            file.seek(self._offset)
            line = file.readline()
            self._offset = file.tell()
        if not line:
            raise Empty
        payload = json.loads(line)
        return LogEvent(
            message=payload["message"],
            level=payload["level"],
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            source=payload["source"],
        )


class GuiLogHandler(logging.Handler):
    """Logging handler that stores formatted records for GUI-side polling."""

    def __init__(self, queue: LogEventQueue, *, level: int = logging.INFO) -> None:
        super().__init__(level)
        self._queue = queue
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = "ERROR" if record.levelno >= logging.ERROR else "WARNING"
            if record.levelno < logging.WARNING:
                level = "INFO"
            event = LogEvent(
                message=self.format(record),
                level=level,
                source=record.name,
            )
            self._queue.put(event)
        except Exception:
            self.handleError(record)


def install_gui_log_handler(
    queue: LogEventQueue | None = None,
) -> tuple[GuiLogHandler, LogEventQueue]:
    """Install a root logger handler and return its queue for GUI polling."""

    queue = queue or Queue()
    handler = GuiLogHandler(queue)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    if root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)
    return handler, queue


def drain_gui_log_queue(
    queue: LogEventQueue,
    session: SessionState,
    *,
    limit: int = 200,
) -> None:
    """Move pending log records into *session* on the Qt main thread."""

    for _index in range(limit):
        try:
            event = queue.get_nowait()
        except (Empty, OSError):
            return
        session.add_log_event(event)
