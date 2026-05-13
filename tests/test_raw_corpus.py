from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

from photo_organizer.constants import RAW_IMAGE_FILE_EXTENSIONS, raw_format_name_for_extension
import photo_organizer.metadata as metadata

FIXTURES_DIR = Path(__file__).parent / "fixtures"
if str(FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURES_DIR))

from raw_corpus import (  # noqa: E402
    RAW_CORPUS_CASES,
    RAW_CORPUS_CORRUPT_CASE,
    RAW_CORPUS_NO_GPS_CASE,
    RAW_CORPUS_VALID_CASES,
    RawCorpusCase,
    build_raw_corpus,
)


def _case_ids(cases: tuple[RawCorpusCase, ...]) -> list[str]:
    return [case.case_id for case in cases]


@pytest.fixture()
def raw_corpus(tmp_path: Path) -> dict[str, Path]:
    return build_raw_corpus(tmp_path / "raw-corpus")


def test_raw_corpus_contains_one_valid_sample_per_supported_raw_format() -> None:
    assert _case_ids(RAW_CORPUS_VALID_CASES) == [
        "apple_proraw_dng",
        "canon_cr2",
        "canon_cr3",
        "canon_crw",
        "nikon_nef",
        "sony_arw",
        "panasonic_rw2",
        "olympus_orf",
        "fujifilm_raf",
    ]
    assert {
        Path(case.relative_path).suffix
        for case in RAW_CORPUS_VALID_CASES
    } == RAW_IMAGE_FILE_EXTENSIONS


@pytest.mark.parametrize(
    "case",
    RAW_CORPUS_VALID_CASES,
    ids=_case_ids(RAW_CORPUS_VALID_CASES),
)
def test_raw_corpus_valid_samples_extract_core_metadata(
    raw_corpus: dict[str, Path],
    case: RawCorpusCase,
) -> None:
    path = raw_corpus[case.case_id]

    fields = metadata.extract_exif_metadata(path)
    resolution = metadata.resolve_best_available_datetime(path, date_heuristics=False)
    coordinates = metadata.extract_gps_coordinates(path)
    camera_profile = metadata.extract_camera_profile(path)

    assert raw_format_name_for_extension(path.suffix) == case.raw_format
    assert fields["Make"] == case.make
    assert fields["Model"] == case.model
    assert resolution.value == case.expected_datetime
    assert resolution.provenance is not None
    assert resolution.provenance.source == "EXIF"
    assert resolution.provenance.field == "DateTimeOriginal"
    assert coordinates is not None
    assert coordinates.latitude == case.expected_latitude
    assert coordinates.longitude == case.expected_longitude
    assert camera_profile == {
        "make": case.make,
        "model": case.model,
        "profile": f"{case.make} {case.model}",
    }


def test_raw_corpus_valid_sample_without_gps_reports_no_coordinates(
    raw_corpus: dict[str, Path],
) -> None:
    path = raw_corpus[RAW_CORPUS_NO_GPS_CASE.case_id]

    fields = metadata.extract_exif_metadata(path)
    resolution = metadata.resolve_best_available_datetime(path, date_heuristics=False)
    coordinates = metadata.extract_gps_coordinates(path)

    assert fields["Make"] == RAW_CORPUS_NO_GPS_CASE.make
    assert fields["Model"] == RAW_CORPUS_NO_GPS_CASE.model
    assert "GPSLatitudeDecimal" not in fields
    assert "GPSLongitudeDecimal" not in fields
    assert resolution.value == RAW_CORPUS_NO_GPS_CASE.expected_datetime
    assert coordinates is None


def test_raw_corpus_corrupt_sample_is_handled_safely(
    raw_corpus: dict[str, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = raw_corpus[RAW_CORPUS_CORRUPT_CASE.case_id]

    with caplog.at_level(logging.WARNING):
        fields = metadata.extract_exif_metadata(path)

    assert fields == {}
    assert "Failed to read RAW metadata" in caplog.text
    with pytest.raises(ValueError, match="No usable date metadata"):
        metadata.resolve_best_available_datetime(path, date_heuristics=False)


def test_raw_corpus_normalizes_metadata_across_manufacturers(
    raw_corpus: dict[str, Path],
) -> None:
    observed = {
        case.case_id: metadata.normalize_metadata_fields(
            exif_fields=metadata.extract_exif_metadata(raw_corpus[case.case_id])
        )
        for case in RAW_CORPUS_VALID_CASES
    }

    for case in RAW_CORPUS_VALID_CASES:
        normalized = observed[case.case_id]
        assert normalized.camera_make is not None
        assert normalized.camera_make.value == case.make
        assert normalized.camera_make.provenance.source == "EXIF"
        assert normalized.camera_model is not None
        assert normalized.camera_model.value == case.model
        assert normalized.camera_model.provenance.source == "EXIF"
        assert normalized.date_taken_candidates[0].value == case.expected_datetime
        assert normalized.gps_coordinates is not None
        assert normalized.gps_coordinates.latitude == case.expected_latitude
        assert normalized.gps_coordinates.longitude == case.expected_longitude


def test_raw_corpus_builder_generates_all_declared_cases(
    raw_corpus: dict[str, Path],
) -> None:
    assert set(raw_corpus) == {case.case_id for case in RAW_CORPUS_CASES}
    assert all(path.is_file() for path in raw_corpus.values())
