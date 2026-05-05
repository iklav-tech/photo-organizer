from __future__ import annotations

import sys
from pathlib import Path

import pytest

import photo_organizer.metadata as metadata

FIXTURES_DIR = Path(__file__).parent / "fixtures"
if str(FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURES_DIR))

from metadata_corpus import (  # noqa: E402
    METADATA_CORPUS_CASES,
    MetadataCorpusCase,
    build_metadata_corpus,
)


def _case_ids(cases: tuple[MetadataCorpusCase, ...]) -> list[str]:
    return [case.case_id for case in cases]


SUCCESS_CASES = tuple(
    case for case in METADATA_CORPUS_CASES if case.expected_value is not None
)


@pytest.fixture()
def metadata_corpus(tmp_path: Path) -> dict[str, Path]:
    return build_metadata_corpus(tmp_path / "metadata-corpus")


def test_metadata_corpus_contains_required_legacy_samples() -> None:
    assert _case_ids(METADATA_CORPUS_CASES) == [
        "jpeg_exif",
        "tiff_tags",
        "iptc_iim",
        "xmp_embedded",
        "xmp_sidecar",
        "png_exif",
        "png_itxt_text",
        "no_metadata",
        "conflicting_metadata",
    ]


@pytest.mark.parametrize("case", SUCCESS_CASES, ids=_case_ids(SUCCESS_CASES))
def test_metadata_corpus_resolves_success_cases(
    metadata_corpus: dict[str, Path],
    case: MetadataCorpusCase,
) -> None:
    resolution = metadata.resolve_best_available_datetime(
        metadata_corpus[case.case_id],
        date_heuristics=False,
    )

    assert resolution.value == case.expected_value
    assert resolution.provenance is not None
    assert resolution.provenance.source == case.expected_source
    assert resolution.provenance.field == case.expected_field
    assert resolution.provenance.confidence == case.expected_confidence
    assert resolution.reconciliation is not None
    assert resolution.reconciliation.conflict is case.expect_conflict


def test_metadata_corpus_reports_absence_when_metadata_is_missing(
    metadata_corpus: dict[str, Path],
) -> None:
    with pytest.raises(ValueError, match="No usable date metadata"):
        metadata.resolve_best_available_datetime(
            metadata_corpus["no_metadata"],
            date_heuristics=False,
        )


def test_metadata_corpus_conflict_keeps_precedence_winner(
    metadata_corpus: dict[str, Path],
) -> None:
    resolution = metadata.resolve_best_available_datetime(
        metadata_corpus["conflicting_metadata"],
        date_heuristics=False,
    )

    assert resolution.reconciliation is not None
    assert resolution.reconciliation.conflict is True
    assert resolution.reconciliation.selected.provenance.label == (
        "EXIF:DateTimeOriginal"
    )
    assert [
        candidate.provenance.label
        for candidate in resolution.reconciliation.candidates
    ] == [
        "EXIF:DateTimeOriginal",
        "XMP:xmp:CreateDate",
    ]


def test_metadata_corpus_covers_date_precedence_matrix(
    metadata_corpus: dict[str, Path],
) -> None:
    observed = {}
    for case in SUCCESS_CASES:
        resolution = metadata.resolve_best_available_datetime(
            metadata_corpus[case.case_id],
            date_heuristics=False,
        )
        assert resolution.provenance is not None
        observed[case.case_id] = (
            resolution.provenance.source,
            resolution.provenance.field,
        )

    assert observed == {
        "jpeg_exif": ("EXIF", "DateTimeOriginal"),
        "tiff_tags": ("EXIF", "CreateDate"),
        "iptc_iim": ("IPTC-IIM", "2:55,2:60"),
        "xmp_embedded": ("XMP", "xmp:CreateDate"),
        "xmp_sidecar": ("XMP sidecar", "xmp:CreateDate"),
        "png_exif": ("EXIF", "DateTimeOriginal"),
        "png_itxt_text": ("XMP", "xmp:CreateDate"),
        "conflicting_metadata": ("EXIF", "DateTimeOriginal"),
    }


def test_metadata_corpus_png_text_sample_exposes_itxt_and_text_chunks(
    metadata_corpus: dict[str, Path],
) -> None:
    png_fields = metadata.extract_png_metadata(metadata_corpus["png_itxt_text"])
    xmp_fields = metadata.extract_xmp_metadata(metadata_corpus["png_itxt_text"])

    assert png_fields["Creation Time"] == "2024:08:15 14:32:09"
    assert png_fields["PNGFieldSources"]["Creation Time"] == "tEXt"
    assert png_fields["PNGFieldSources"]["XML:com.adobe.xmp"] == "iTXt"
    assert xmp_fields["xmp:CreateDate"] == "2024-08-15T14:32:09"


def test_metadata_corpus_iptc_sample_exposes_legacy_iim_fields(
    metadata_corpus: dict[str, Path],
) -> None:
    fields = metadata.extract_iptc_iim_metadata(metadata_corpus["iptc_iim"])

    assert fields["DateCreated"] == "20240815"
    assert fields["TimeCreated"] == "143209"
    assert fields["City"] == "Paraty"
    assert fields["IPTCIIMFieldSources"]["DateCreated"] == "2:55"
