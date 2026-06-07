"""Terminal-style log console for GUI events and backend logs."""

from __future__ import annotations

from html import escape

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from photo_organizer.gui.session import LogEvent
from photo_organizer.gui.theme import COLORS, set_theme_role


class LogConsole(QTextEdit):
    """Read-only chronological log console with severity coloring."""

    _LEVEL_COLORS = {
        "INFO": COLORS.success,
        "WARNING": COLORS.warning,
        "ERROR": COLORS.error,
    }

    def __init__(self, *, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setUndoRedoEnabled(False)
        self.document().setMaximumBlockCount(2000)
        self.setPlaceholderText("System engine output will appear here...")
        set_theme_role(self, "logPanel")

    def append_event(self, event: LogEvent) -> None:
        timestamp = escape(event.timestamp.strftime("%H:%M:%S"))
        level = escape(event.level)
        source = escape(event.source)
        message = escape(event.message)
        color = self._LEVEL_COLORS.get(event.level, COLORS.on_surface_variant)
        self.append(
            (
                f'<span style="color:{COLORS.muted}">{timestamp}</span> '
                f'<span style="color:{color}; font-weight:600">[{level}]</span> '
                f'<span style="color:{COLORS.primary_dim}">{source}</span> '
                f'<span style="color:{COLORS.primary_soft}">{message}</span>'
            )
        )
        self.moveCursor(QTextCursor.MoveOperation.End)

    def append_output(
        self,
        text: str,
        *,
        level: str = "INFO",
        source: str = "task",
    ) -> None:
        for line in text.splitlines():
            self.append_event(LogEvent(message=line, level=level, source=source))

    def set_plain_output(
        self,
        text: str,
        *,
        level: str = "INFO",
        source: str = "task",
    ) -> None:
        self.append_output(text, level=level, source=source)
