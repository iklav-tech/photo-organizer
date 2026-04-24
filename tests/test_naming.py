from datetime import datetime
import re

import pytest

from photo_organizer.naming import build_default_filename


def test_build_default_filename_matches_expected_format() -> None:
    dt = datetime(2024, 8, 15, 14, 32, 9)

    result = build_default_filename(dt, "IMG_1034.jpg")

    assert result == "2024-08-15_14-32-09.jpg"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.jpg", result)


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("photo.jpeg", "2024-01-02_03-04-05.jpeg"),
        ("photo.PNG", "2024-01-02_03-04-05.PNG"),
    ],
)
def test_build_default_filename_preserves_original_extension(
    original: str, expected: str
) -> None:
    dt = datetime(2024, 1, 2, 3, 4, 5)

    assert build_default_filename(dt, original) == expected


def test_build_default_filename_is_deterministic() -> None:
    dt = datetime(2023, 12, 31, 23, 59, 59)
    original = "holiday.png"

    first = build_default_filename(dt, original)
    second = build_default_filename(dt, original)

    assert first == second
