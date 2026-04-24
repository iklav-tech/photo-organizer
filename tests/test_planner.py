from datetime import datetime
from pathlib import Path, PureWindowsPath

import photo_organizer.planner as planner


def test_build_date_destination_uses_yyyy_mm_dd_pattern() -> None:
    base_dir = Path("organized")
    dt = datetime(2024, 8, 15, 14, 32, 9)

    result = planner.build_date_destination(base_dir, dt)

    assert result == Path("organized") / "2024" / "08" / "15"


def test_build_date_destination_for_file_uses_resolved_date(monkeypatch) -> None:
    resolved_dt = datetime(2021, 1, 2, 3, 4, 5)
    monkeypatch.setattr(
        planner,
        "get_best_available_datetime",
        lambda _file_path: resolved_dt,
    )

    result = planner.build_date_destination_for_file("output", "photo.jpg")

    assert result == Path("output") / "2021" / "01" / "02"


def test_build_date_destination_supports_windows_pathlib_paths() -> None:
    base_dir = PureWindowsPath("C:/OrganizedPhotos")
    dt = datetime(2023, 12, 5, 6, 7, 8)

    result = planner.build_date_destination(base_dir, dt)

    assert result == PureWindowsPath("C:/OrganizedPhotos/2023/12/05")
