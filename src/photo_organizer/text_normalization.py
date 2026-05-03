"""Text normalization helpers for legacy metadata and generated paths."""

from __future__ import annotations

from dataclasses import dataclass
import re
import sys
import unicodedata


INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\u00e2\u20ac")


@dataclass(frozen=True)
class TextNormalizationResult:
    """Normalized text plus report-friendly change details."""

    value: str
    original: str
    changes: tuple[str, ...] = ()
    fidelity_loss: bool = False

    @property
    def changed(self) -> bool:
        return self.value != self.original or bool(self.changes)


def _decode_bytes(value: bytes) -> tuple[str, list[str], bool]:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            decoded = value.decode(encoding)
        except UnicodeDecodeError:
            continue
        return decoded, [f"decoded bytes as {encoding}"], False

    return value.decode("utf-8", errors="replace"), [
        "decoded bytes with replacement characters"
    ], True


def _repair_latin1_mojibake(text: str) -> tuple[str, bool]:
    if not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text, False

    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text, False

    if repaired == text:
        return text, False
    return repaired, True


def normalize_text(
    value: str | bytes,
    *,
    legacy_encoding: bool = True,
) -> TextNormalizationResult:
    """Normalize text to NFC and repair common legacy mojibake when possible."""
    changes: list[str] = []
    fidelity_loss = False

    if isinstance(value, bytes):
        text, decode_changes, decode_loss = _decode_bytes(value)
        changes.extend(decode_changes)
        fidelity_loss = fidelity_loss or decode_loss
    else:
        text = str(value)

    original = text

    if legacy_encoding:
        repaired, did_repair = _repair_latin1_mojibake(text)
        if did_repair:
            text = repaired
            changes.append("repaired legacy charset mojibake")

    without_surrogates = text.encode("utf-8", errors="replace").decode("utf-8")
    if without_surrogates != text:
        text = without_surrogates
        changes.append("replaced non-UTF-8 text")
        fidelity_loss = True

    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        text = normalized
        changes.append("normalized Unicode to NFC")

    return TextNormalizationResult(
        value=text,
        original=original,
        changes=tuple(changes),
        fidelity_loss=fidelity_loss,
    )


def normalize_path_part(
    value: str | None,
    *,
    default: str = "Unknown",
) -> TextNormalizationResult:
    """Normalize a single filename/folder component and replace invalid characters."""
    if value is None:
        return TextNormalizationResult(value=default, original="", changes=())

    result = normalize_text(value)
    text = result.value.strip()
    changes = list(result.changes)
    fidelity_loss = result.fidelity_loss

    cleaned = INVALID_PATH_CHARS_RE.sub("-", text)
    if cleaned != text:
        text = cleaned
        changes.append("replaced invalid path characters")
        fidelity_loss = True

    collapsed = re.sub(r"\s+", " ", text).strip(" .")
    if collapsed != text:
        text = collapsed
        changes.append("trimmed or collapsed whitespace")

    if not text:
        text = default
        changes.append("used default for empty text")
        fidelity_loss = True

    fs_encoding = sys.getfilesystemencoding() or "utf-8"
    encoded = text.encode(fs_encoding, errors="replace")
    round_tripped = encoded.decode(fs_encoding, errors="replace")
    if round_tripped != text:
        text = round_tripped
        changes.append(f"replaced text not encodable as {fs_encoding}")
        fidelity_loss = True

    return TextNormalizationResult(
        value=text,
        original=result.original,
        changes=tuple(changes),
        fidelity_loss=fidelity_loss,
    )


def describe_text_normalization(
    field: str,
    result: TextNormalizationResult,
) -> str | None:
    """Return a compact report observation for one normalized field."""
    if not result.changed:
        return None

    suffix = "; fidelity loss" if result.fidelity_loss else ""
    return f"{field}: {'; '.join(result.changes)}{suffix}"
