from __future__ import annotations

import csv
import json

import pytest

from photo_organizer.journal import JournalWriter, load_completed_sources


def test_jsonl_journal_writes_entries_and_loads_only_successful_sources(tmp_path) -> None:
    journal_path = tmp_path / "journal.jsonl"

    with JournalWriter.open(
        journal_path,
        command="organize",
        session_id="session-001",
    ) as journal:
        journal.write_entry(
            action="copy",
            source=tmp_path / "a.jpg",
            destination=tmp_path / "out" / "a.jpg",
            status="success",
            date_value="2024-08-15T14:32:09",
            date_source="EXIF",
            date_confidence="high",
            date_kind="captured",
            staging=True,
        )
        journal.write_entry(
            action="copy",
            source=tmp_path / "failed.jpg",
            destination=tmp_path / "out" / "failed.jpg",
            status="error",
            error="copy failed",
        )
        assert journal.entries_written == 2

    rows = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["session_id"] == "session-001"
    assert rows[0]["command"] == "organize"
    assert rows[0]["status"] == "success"
    assert rows[0]["date_source"] == "EXIF"
    assert rows[0]["staging"] is True
    assert rows[1]["status"] == "error"

    assert load_completed_sources(journal_path) == frozenset({str(tmp_path / "a.jpg")})


def test_csv_journal_writes_header_once_and_loads_completed_sources(tmp_path) -> None:
    journal_path = tmp_path / "journal.csv"

    with JournalWriter.open(
        journal_path,
        command="import",
        session_id="session-001",
    ) as journal:
        journal.write_entry(
            action="copy",
            source="source-1.jpg",
            destination="dest-1.jpg",
            status="success",
            burst_group_id="event-001",
            burst_mark="BURST",
        )

    with JournalWriter.open(
        journal_path,
        command="import",
        session_id="session-002",
    ) as journal:
        journal.write_entry(
            action="dry-run",
            source="source-2.jpg",
            destination="dest-2.jpg",
            status="dry-run",
        )

    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("timestamp,session_id,command")
    assert sum(1 for line in lines if line.startswith("timestamp,")) == 1

    with journal_path.open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert [row["session_id"] for row in rows] == ["session-001", "session-002"]
    assert rows[0]["burst_group_id"] == "event-001"
    assert rows[0]["burst_mark"] == "BURST"
    assert rows[1]["status"] == "dry-run"

    assert load_completed_sources(journal_path) == frozenset({"source-1.jpg"})


def test_load_completed_sources_ignores_malformed_jsonl_and_non_success_entries(
    tmp_path,
) -> None:
    journal_path = tmp_path / "journal.ndjson"
    journal_path.write_text(
        "\n".join(
            [
                '{"status": "success", "source": "ok.jpg"}',
                "{not-json",
                '{"status": "error", "source": "retry.jpg"}',
                '{"status": "dry-run", "source": "simulated.jpg"}',
                '{"status": "success"}',
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert load_completed_sources(journal_path) == frozenset({"ok.jpg"})


def test_journal_rejects_unsupported_extension(tmp_path) -> None:
    with pytest.raises(ValueError, match="Journal path must end"):
        JournalWriter.open(tmp_path / "journal.txt", command="organize")

    unsupported_existing = tmp_path / "journal.txt"
    unsupported_existing.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="Journal path must end"):
        load_completed_sources(unsupported_existing)
