"""Append-only operation journal for audit and debug.

Every import or organize session can write a structured journal that records
each file operation as it happens.  The journal is flushed after every entry
so a crash mid-run still captures the work already done.

Supported formats
-----------------
- **JSONL** (``.jsonl`` / ``.ndjson``): one JSON object per line.  Easy to
  stream, grep and load into pandas or jq.
- **CSV** (``.csv``): spreadsheet-friendly, one row per operation.

Entry fields
------------
``timestamp``
    ISO-8601 UTC timestamp of when the operation completed (or failed).
``session_id``
    A short random hex token that groups all entries from a single run.
``command``
    The CLI sub-command that produced this entry (``organize``, ``import``, …).
``action``
    ``copy``, ``move``, or ``dry-run``.
``source``
    Absolute path of the source file.
``destination``
    Absolute path of the intended destination file.
``status``
    ``success``, ``error``, or ``dry-run``.
``error``
    Error message when *status* is ``error``, empty otherwise.
``date_value``
    ISO-8601 datetime chosen for the file, empty when unavailable.
``date_source``
    Metadata source that provided the date (e.g. ``EXIF``, ``filesystem``).
``date_confidence``
    Confidence level: ``high``, ``medium``, or ``low``.
``date_kind``
    ``captured`` or ``inferred``.
``clock_offset``
    Clock offset applied to this file, empty when none.
``event_name``
    Event name from the correction manifest, empty when none.
``staging``
    ``true`` when the operation went through a staging directory.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Literal


logger = logging.getLogger(__name__)

JOURNAL_EXTENSIONS = frozenset({".jsonl", ".ndjson", ".csv"})

JournalFormat = Literal["jsonl", "csv"]

# Ordered list of CSV column names — also used as the canonical field order for
# JSONL entries so tooling can rely on a stable schema.
JOURNAL_FIELDS = (
    "timestamp",
    "session_id",
    "command",
    "action",
    "source",
    "destination",
    "status",
    "error",
    "date_value",
    "date_source",
    "date_confidence",
    "date_kind",
    "clock_offset",
    "event_name",
    "staging",
)


def _detect_format(path: Path) -> JournalFormat:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".jsonl", ".ndjson"}:
        return "jsonl"
    raise ValueError(
        f"Journal path must end with .jsonl, .ndjson or .csv — got: {path.name}"
    )


def _new_session_id() -> str:
    return secrets.token_hex(6)


class JournalWriter:
    """Append-only writer for a single session's operation journal.

    Usage::

        with JournalWriter.open("ops.jsonl", command="organize") as journal:
            journal.write_entry(operation, status="success")

    The file is opened in append mode so multiple sessions accumulate in the
    same file.  A CSV journal writes a header row only when the file is new or
    empty.  Each :meth:`write_entry` call flushes immediately so partial runs
    are always recoverable.
    """

    def __init__(
        self,
        path: Path,
        fmt: JournalFormat,
        session_id: str,
        command: str,
        file_handle: IO[str],
        csv_writer: csv.DictWriter | None,
    ) -> None:
        self._path = path
        self._fmt = fmt
        self._session_id = session_id
        self._command = command
        self._fh = file_handle
        self._csv_writer = csv_writer
        self._count = 0

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        command: str,
        session_id: str | None = None,
    ) -> "JournalWriter":
        """Open (or create) a journal file and return a :class:`JournalWriter`.

        The file is opened in append mode.  For CSV journals the header row is
        written only when the file is new or empty.
        """
        journal_path = Path(path)
        fmt = _detect_format(journal_path)
        sid = session_id or _new_session_id()

        journal_path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not journal_path.exists() or journal_path.stat().st_size == 0

        fh: IO[str] = journal_path.open("a", encoding="utf-8", newline="")

        csv_writer: csv.DictWriter | None = None
        if fmt == "csv":
            csv_writer = csv.DictWriter(fh, fieldnames=list(JOURNAL_FIELDS))
            if is_new:
                csv_writer.writeheader()
                fh.flush()

        return cls(
            path=journal_path,
            fmt=fmt,
            session_id=sid,
            command=command,
            file_handle=fh,
            csv_writer=csv_writer,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def path(self) -> Path:
        return self._path

    @property
    def entries_written(self) -> int:
        return self._count

    def write_entry(
        self,
        *,
        action: str,
        source: str | Path,
        destination: str | Path,
        status: str,
        error: str = "",
        date_value: str = "",
        date_source: str = "",
        date_confidence: str = "",
        date_kind: str = "",
        clock_offset: str = "",
        event_name: str = "",
        staging: bool = False,
    ) -> None:
        """Append one entry to the journal and flush immediately."""
        entry: dict[str, object] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "session_id": self._session_id,
            "command": self._command,
            "action": action,
            "source": str(source),
            "destination": str(destination),
            "status": status,
            "error": error,
            "date_value": date_value,
            "date_source": date_source,
            "date_confidence": date_confidence,
            "date_kind": date_kind,
            "clock_offset": clock_offset,
            "event_name": event_name,
            "staging": staging,
        }
        try:
            if self._fmt == "jsonl":
                self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            else:
                assert self._csv_writer is not None
                # CSV writer expects str values for all fields.
                self._csv_writer.writerow(
                    {k: str(v) if not isinstance(v, str) else v for k, v in entry.items()}
                )
            self._fh.flush()
            self._count += 1
        except OSError as exc:
            logger.warning(
                "Failed to write journal entry: path=%s error=%s",
                self._path,
                exc,
            )

    def close(self) -> None:
        """Flush and close the underlying file handle."""
        try:
            self._fh.flush()
            self._fh.close()
        except OSError as exc:  # pragma: no cover
            logger.warning("Failed to close journal: path=%s error=%s", self._path, exc)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "JournalWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def _entry_fields_from_operation(operation: object) -> dict[str, str]:
    """Extract journal fields from a :class:`~photo_organizer.executor.FileOperation`."""
    date_value = ""
    date_source = ""
    date_confidence = ""
    date_kind = getattr(operation, "date_kind", "") or ""
    clock_offset = ""
    event_name = ""

    prov = getattr(operation, "date_provenance", None)
    if prov is not None:
        date_source = getattr(prov, "source", "") or ""
        date_confidence = getattr(prov, "confidence", "") or ""
        raw = getattr(prov, "raw_value", None)
        # The raw_value for a clock-offset correction is a dict with base_value.
        if isinstance(raw, dict) and "base_value" in raw:
            date_value = str(raw.get("base_value", ""))
        elif isinstance(raw, str):
            date_value = raw
        # Try to get the resolved datetime from the operation itself.
        # We don't store it directly, but the provenance label carries the source.

    correction = getattr(operation, "correction_manifest", None)
    if correction is not None:
        clock_offset = getattr(correction, "clock_offset", "") or ""
        event_name = getattr(correction, "event_name", "") or ""

    return {
        "date_value": date_value,
        "date_source": date_source,
        "date_confidence": date_confidence,
        "date_kind": date_kind,
        "clock_offset": clock_offset,
        "event_name": event_name,
    }


def load_completed_sources(path: str | Path) -> frozenset[str]:
    """Read a journal file and return the set of source paths that succeeded.

    Only entries with ``status == "success"`` are included.  Entries with
    ``status == "error"`` or ``status == "dry-run"`` are intentionally excluded
    so that failed or simulated operations are always retried on resume.

    Malformed lines are silently skipped so a partially-written journal never
    blocks a resume.

    Returns a :class:`frozenset` of normalised absolute path strings so that
    membership tests are O(1).
    """
    journal_path = Path(path)
    if not journal_path.exists():
        return frozenset()

    completed: set[str] = set()
    fmt = _detect_format(journal_path)

    try:
        if fmt == "jsonl":
            with journal_path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (
                        isinstance(entry, dict)
                        and entry.get("status") == "success"
                        and entry.get("source")
                    ):
                        completed.add(str(entry["source"]))
        else:
            # CSV format
            with journal_path.open(encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if row.get("status") == "success" and row.get("source"):
                        completed.add(str(row["source"]))
    except OSError as exc:
        logger.warning(
            "Could not read journal for resume: path=%s error=%s",
            journal_path,
            exc,
        )

    return frozenset(completed)
