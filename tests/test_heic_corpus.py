from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import json
import sys

import pytest

from photo_organizer.cli import main
import photo_organizer.metadata as metadata

FIXTURES_DIR = Path(__file__).parent / "fixtures"
if str(FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURES_DIR))

from heic_corpus import (  # noqa: E402
    EXPECTED_HEIC_DATETIME,
    HeicCorpus,
    build_heic_corpus,
    ensure_heic_writer_available,
)


def test_heic_corpus_contains_required_samples(
    heic_corpus: HeicCorpus,
) -> None:
    assert heic_corpus.with_exif_gps.suffix == ".HEIC"
    assert heic_corpus.with_exif_no_gps.suffix == ".HEIC"
    assert heic_corpus.without_exif.suffix == ".HEIC"
    assert heic_corpus.malformed.suffix == ".HEIC"


@pytest.fixture()
def heic_corpus(tmp_path: Path) -> HeicCorpus:
    try:
        ensure_heic_writer_available(tmp_path)
    except RuntimeError as exc:
        pytest.skip(str(exc))
    return build_heic_corpus(tmp_path / "heic-corpus")


def test_heic_corpus_date_reads_iphone_like_exif(
    heic_corpus: HeicCorpus,
) -> None:
    resolution = metadata.resolve_best_available_datetime(
        heic_corpus.with_exif_gps,
        date_heuristics=False,
    )

    assert resolution.value == EXPECTED_HEIC_DATETIME
    assert resolution.provenance is not None
    assert resolution.provenance.source == "EXIF"
    assert resolution.provenance.field == "DateTimeOriginal"


def test_heic_corpus_gps_reads_iphone_like_exif(
    heic_corpus: HeicCorpus,
) -> None:
    coordinates = metadata.extract_gps_coordinates(heic_corpus.with_exif_gps)

    assert coordinates is not None
    assert coordinates.latitude == -23.5
    assert coordinates.longitude == -46.625
    assert coordinates.provenance is not None
    assert coordinates.provenance.source == "EXIF"
    assert coordinates.provenance.field == "GPSInfo"


def test_heic_corpus_reports_absent_gps(
    heic_corpus: HeicCorpus,
) -> None:
    assert metadata.extract_gps_coordinates(heic_corpus.with_exif_no_gps) is None


def test_heic_corpus_reports_absent_exif_date(
    heic_corpus: HeicCorpus,
) -> None:
    with pytest.raises(ValueError, match="No usable date metadata"):
        metadata.resolve_best_available_datetime(
            heic_corpus.without_exif,
            date_heuristics=False,
        )


def test_heic_corpus_handles_read_error_safely(
    heic_corpus: HeicCorpus,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        fields = metadata.extract_exif_metadata(heic_corpus.malformed)

    assert fields == {}
    assert "Failed to read HEIF metadata" in caplog.text


def test_organize_pipeline_copies_real_heic_with_exif(
    tmp_path: Path,
    heic_corpus: HeicCorpus,
) -> None:
    output_dir = tmp_path / "organized"
    expected_destination = (
        output_dir / "2024" / "05" / "06" / "2024-05-06_07-08-09.HEIC"
    )

    result = main([
        "organize",
        str(heic_corpus.with_exif_gps.parent.parent),
        "--output",
        str(output_dir),
        "--copy",
        "--no-date-heuristics",
    ])

    assert result == 0
    assert heic_corpus.with_exif_gps.exists()
    assert expected_destination.exists()
    assert expected_destination.read_bytes() == heic_corpus.with_exif_gps.read_bytes()


def test_organize_dry_run_pipeline_plans_real_heic_without_writing(
    tmp_path: Path,
    heic_corpus: HeicCorpus,
) -> None:
    output_dir = tmp_path / "organized"

    result = main([
        "organize",
        str(heic_corpus.with_exif_gps.parent),
        "--output",
        str(output_dir),
        "--dry-run",
        "--no-date-heuristics",
    ])

    assert result == 0
    assert heic_corpus.with_exif_gps.exists()
    assert not output_dir.exists()


def test_inspect_pipeline_reports_real_heic_audit(
    tmp_path: Path,
    heic_corpus: HeicCorpus,
) -> None:
    report_path = tmp_path / "heic-audit.json"

    result = main([
        "inspect",
        str(heic_corpus.with_exif_gps.parent),
        "--report",
        str(report_path),
        "--no-date-heuristics",
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    file_report = report["files"][0]
    assert file_report["heif"]["format"] == "HEIF/HEIC"
    assert file_report["heif"]["found_metadata"] == ["EXIF", "HEIF container"]
    assert file_report["heif"]["date_evidence"]["kind"] == "real-metadata"
    assert file_report["heif"]["location_evidence"]["kind"] == "real-gps"
