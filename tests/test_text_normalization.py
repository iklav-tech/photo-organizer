from __future__ import annotations

from photo_organizer.text_normalization import (
    describe_text_normalization,
    normalize_path_part,
    normalize_text,
)


def test_normalize_text_decodes_bytes_and_repairs_common_mojibake() -> None:
    decoded = normalize_text("São Paulo".encode("utf-8"))

    assert decoded.value == "São Paulo"
    assert decoded.changes == ("decoded bytes as utf-8",)
    assert decoded.changed is True
    assert decoded.fidelity_loss is False

    repaired = normalize_text("SÃ£o Paulo")
    assert repaired.value == "São Paulo"
    assert repaired.changes == ("repaired legacy charset mojibake",)


def test_normalize_text_normalizes_unicode_to_nfc() -> None:
    result = normalize_text("Cafe\u0301")

    assert result.value == "Café"
    assert result.original == "Cafe\u0301"
    assert result.changes == ("normalized Unicode to NFC",)


def test_normalize_path_part_replaces_invalid_chars_and_empty_values() -> None:
    result = normalize_path_part('  Album: 2024 / Fotos*\nNovas  ')

    assert result.value == "Album- 2024 - Fotos--Novas"
    assert "replaced invalid path characters" in result.changes
    assert result.fidelity_loss is True

    spaced = normalize_path_part("Album   Novo")
    assert spaced.value == "Album Novo"
    assert "trimmed or collapsed whitespace" in spaced.changes

    empty = normalize_path_part(" . \t", default="UnknownLocation")
    assert empty.value == "UnknownLocation"
    assert "used default for empty text" in empty.changes
    assert empty.fidelity_loss is True


def test_describe_text_normalization_reports_changes_and_fidelity_loss() -> None:
    result = normalize_path_part("bad/name", default="Unknown")

    assert describe_text_normalization("city", result) == (
        "city: replaced invalid path characters; fidelity loss"
    )
    assert describe_text_normalization("city", normalize_text("Paraty")) is None
