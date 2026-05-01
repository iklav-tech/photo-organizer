from datetime import datetime
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

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


def test_build_location_destination_uses_country_state_city_pattern() -> None:
    location = SimpleNamespace(
        country="Brazil",
        state="Sao Paulo",
        city="Sao Paulo",
    )

    result = planner.build_location_destination("organized", location)

    assert result == Path("organized") / "Brazil" / "Sao Paulo" / "Sao Paulo"


def test_build_location_destination_sanitizes_folder_names() -> None:
    location = SimpleNamespace(
        country="Brasil",
        state="Rio/Minas",
        city="  Sao  Tome:*  ",
    )

    result = planner.build_location_destination("organized", location)

    assert result == Path("organized") / "Brasil" / "Rio-Minas" / "Sao Tome--"


def test_build_location_date_destination_uses_location_and_year_month() -> None:
    location = SimpleNamespace(
        country="Brasil",
        state="RJ",
        city="Paraty",
    )
    dt = datetime(2024, 8, 15, 14, 32, 9)

    result = planner.build_location_date_destination("organized", location, dt)

    assert result == Path("organized") / "Brasil" / "RJ" / "Paraty" / "2024" / "08"


def test_build_city_state_month_destination_uses_city_state_and_year_month() -> None:
    location = SimpleNamespace(
        country="Brasil",
        state="RJ",
        city="Paraty",
    )
    dt = datetime(2024, 8, 15, 14, 32, 9)

    result = planner.build_city_state_month_destination("organized", location, dt)

    assert result == Path("organized") / "Paraty-RJ" / "2024-08"


def test_build_city_state_month_destination_sanitizes_location_parts() -> None:
    location = SimpleNamespace(
        country="Brasil",
        state="Rio/Minas",
        city="  Sao  Tome:*  ",
    )
    dt = datetime(2024, 8, 15, 14, 32, 9)

    result = planner.build_city_state_month_destination("organized", location, dt)

    assert result == Path("organized") / "Sao Tome---Rio-Minas" / "2024-08"


def test_build_pattern_destination_uses_configured_date_and_location_parts() -> None:
    location = SimpleNamespace(
        country="Brasil",
        state="Sao Paulo",
        city="Sao Paulo",
    )
    dt = datetime(2024, 8, 15, 14, 32, 9)

    result = planner.build_pattern_destination(
        "organized",
        dt,
        "{country}/{date:%Y}/{date:%m}",
        location,
    )

    assert result == Path("organized") / "Brasil" / "2024" / "08"


def test_build_pattern_destination_sanitizes_rendered_parts() -> None:
    location = SimpleNamespace(
        country="Brasil",
        state="Rio/Minas",
        city="  Sao  Tome:*  ",
    )
    dt = datetime(2024, 8, 15, 14, 32, 9)

    result = planner.build_pattern_destination(
        "organized",
        dt,
        "{state}/{city}",
        location,
    )

    assert result == Path("organized") / "Rio-Minas" / "Sao Tome--"
