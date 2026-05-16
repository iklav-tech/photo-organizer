from pathlib import Path
from datetime import datetime
import logging
import os

import pytest

from photo_organizer.correction_manifest import CorrectionManifest, CorrectionRule
from photo_organizer.executor import (
    DestinationConflictError,
    FileOperation,
    apply_operations,
    assign_temporal_events,
    find_related_sidecars,
    plan_organization_operations,
)
from photo_organizer.geocoding import ReverseGeocodedLocation
from photo_organizer.metadata import GPSCoordinates
from photo_organizer.metadata import DateTimeResolution


def _iptc_dataset(record: int, dataset: int, value: str) -> bytes:
    raw_value = value.encode("utf-8")
    return (
        b"\x1c"
        + bytes([record, dataset])
        + len(raw_value).to_bytes(2, "big")
        + raw_value
    )


def test_apply_operations_dry_run_move_does_not_modify_files(tmp_path: Path) -> None:
    source = tmp_path / "input.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "input.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=True,
    )

    assert source.exists()
    assert not destination.exists()
    assert logs == [f"[DRY-RUN] MOVE {source} -> {destination}"]


def test_apply_operations_dry_run_copy_does_not_modify_files(tmp_path: Path) -> None:
    source = tmp_path / "input.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "input.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=True,
    )

    assert source.exists()
    assert not destination.exists()
    assert logs == [f"[DRY-RUN] COPY {source} -> {destination}"]


def test_find_related_sidecars_detects_raw_same_basename_xmp(tmp_path: Path) -> None:
    raw = tmp_path / "IMG_0001.CR2"
    sidecar = tmp_path / "IMG_0001.xmp"
    unrelated = tmp_path / "IMG_0002.xmp"
    raw.write_text("raw")
    sidecar.write_text("xmp")
    unrelated.write_text("other")

    assert find_related_sidecars(raw) == (sidecar,)


def test_plan_organization_operations_links_raw_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    raw = source_dir / "IMG_0001.cr2"
    sidecar = source_dir / "IMG_0001.xmp"
    raw.write_text("raw")
    sidecar.write_text("xmp")

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p, **_kwargs: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(source_dir, output_dir, mode="copy")

    assert len(operations) == 1
    assert operations[0].source == raw
    assert operations[0].related_sidecars == (sidecar,)


def test_plan_organization_operations_marks_raw_dng_candidate_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    raw = source_dir / "IMG_0001.cr3"
    raw.write_text("raw")

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p, **_kwargs: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        dng_candidates=True,
    )

    assert len(operations) == 1
    assert operations[0].dng_candidate is True
    assert operations[0].dng_candidate_reason == (
        "RAW file selected for optional DNG interoperability workflow"
    )


def test_plan_organization_operations_classifies_apple_proraw_dng_flow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    raw = source_dir / "IMG_0001.dng"
    raw.write_text("raw")

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p, **_kwargs: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(source_dir, output_dir, mode="copy")

    assert len(operations) == 1
    assert operations[0].raw_format == "Apple ProRAW"
    assert operations[0].raw_flow == "Apple ProRAW / Linear DNG"
    assert operations[0].dng_candidate is False


def test_plan_organization_operations_does_not_mark_dng_candidate_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    raw = source_dir / "IMG_0001.nef"
    raw.write_text("raw")

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p, **_kwargs: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(source_dir, output_dir, mode="copy")

    assert len(operations) == 1
    assert operations[0].dng_candidate is False
    assert operations[0].dng_candidate_reason == ""


def test_plan_organization_operations_segregates_derived_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "IMG_0001_edited.jpg"
    image.write_text("derived")

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p, **_kwargs: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        segregate_derivatives=True,
    )

    assert operations[0].destination == (
        output_dir / "Derivatives" / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )
    assert operations[0].asset_role == "derived"
    assert operations[0].derived is True
    assert operations[0].derived_reason == "matched pattern *_edit*"


def test_plan_organization_operations_uses_configured_derivative_patterns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "album-proof.jpg"
    image.write_text("proof")

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p, **_kwargs: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        segregate_derivatives=True,
        derivative_path="Working",
        derivative_patterns=("*-proof",),
    )

    assert operations[0].destination == (
        output_dir / "Working" / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )
    assert operations[0].asset_role == "derived"
    assert operations[0].derived_reason == "matched pattern *-proof"


def test_assign_temporal_events_groups_by_configured_window(tmp_path: Path) -> None:
    output_dir = tmp_path / "organized"
    operations = [
        FileOperation(
            source=tmp_path / "a.jpg",
            destination=output_dir / "2024" / "08" / "15" / "a.jpg",
            mode="copy",
            chosen_date=datetime(2024, 8, 15, 10, 0),
        ),
        FileOperation(
            source=tmp_path / "b.jpg",
            destination=output_dir / "2024" / "08" / "15" / "b.jpg",
            mode="copy",
            chosen_date=datetime(2024, 8, 15, 10, 20),
        ),
        FileOperation(
            source=tmp_path / "c.jpg",
            destination=output_dir / "2024" / "08" / "15" / "c.jpg",
            mode="copy",
            chosen_date=datetime(2024, 8, 15, 11, 0),
        ),
    ]

    grouped = assign_temporal_events(operations, window_minutes=30)

    assert [operation.temporal_event_id for operation in grouped] == [
        "event-001",
        "event-001",
        "event-002",
    ]
    assert grouped[0].temporal_event_label == "event-001_2024-08-15_10-00"
    assert grouped[0].temporal_event_size == 2
    assert grouped[2].temporal_event_size == 1
    assert grouped[0].destination == operations[0].destination


def test_assign_temporal_events_can_prefix_destination_directory(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "organized"
    destination = output_dir / "2024" / "08" / "15" / "a.jpg"
    operations = [
        FileOperation(
            source=tmp_path / "a.jpg",
            destination=destination,
            mode="copy",
            chosen_date=datetime(2024, 8, 15, 10, 0),
        ),
    ]

    grouped = assign_temporal_events(
        operations,
        window_minutes=30,
        output_dir=output_dir,
        use_event_directory=True,
    )

    assert grouped[0].destination == (
        output_dir
        / "event-001_2024-08-15_10-00"
        / "2024"
        / "08"
        / "15"
        / "a.jpg"
    )


def test_plan_organization_operations_assigns_temporal_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    first = source_dir / "a.jpg"
    second = source_dir / "b.jpg"
    first.write_text("a")
    second.write_text("b")
    dates = {
        first: datetime(2024, 8, 15, 10, 0),
        second: datetime(2024, 8, 15, 10, 10),
    }

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda path, **_kwargs: DateTimeResolution(
            value=dates[path],
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        event_window_minutes=30,
        event_directory=True,
    )

    assert {operation.temporal_event_id for operation in operations} == {"event-001"}
    assert all(
        "event-001_2024-08-15_10-00" in operation.destination.parts
        for operation in operations
    )


def test_apply_operations_copies_raw_sidecar_with_destination_basename(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "IMG_0001.cr2"
    sidecar = tmp_path / "IMG_0001.xmp"
    raw.write_text("raw")
    sidecar.write_text("xmp")
    destination = tmp_path / "out" / "2024-08-15_14-32-09.cr2"

    logs = apply_operations([
        FileOperation(
            source=raw,
            destination=destination,
            mode="copy",
            related_sidecars=(sidecar,),
        )
    ])

    assert logs == [f"[INFO] COPY {raw} -> {destination}"]
    assert raw.exists()
    assert sidecar.exists()
    assert destination.read_text() == "raw"
    assert destination.with_suffix(".xmp").read_text() == "xmp"


def test_apply_operations_avoids_raw_sidecar_destination_collision(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "IMG_0001.cr2"
    sidecar = tmp_path / "IMG_0001.xmp"
    raw.write_text("raw")
    sidecar.write_text("xmp")
    destination = tmp_path / "out" / "2024-08-15_14-32-09.cr2"
    destination.parent.mkdir(parents=True)
    destination.with_suffix(".xmp").write_text("existing-sidecar")

    logs = apply_operations([
        FileOperation(
            source=raw,
            destination=destination,
            mode="copy",
            related_sidecars=(sidecar,),
        )
    ])

    resolved_destination = destination.with_name("2024-08-15_14-32-09_01.cr2")
    assert logs == [f"[INFO] COPY {raw} -> {resolved_destination}"]
    assert destination.with_suffix(".xmp").read_text() == "existing-sidecar"
    assert resolved_destination.read_text() == "raw"
    assert resolved_destination.with_suffix(".xmp").read_text() == "xmp"


def test_apply_operations_moves_raw_sidecar_with_destination_basename(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "IMG_0001.nef"
    sidecar = tmp_path / "IMG_0001.xmp"
    raw.write_text("raw")
    sidecar.write_text("xmp")
    destination = tmp_path / "out" / "2024-08-15_14-32-09.nef"

    logs = apply_operations([
        FileOperation(
            source=raw,
            destination=destination,
            mode="move",
            related_sidecars=(sidecar,),
        )
    ])

    assert logs == [f"[INFO] MOVE {raw} -> {destination}"]
    assert not raw.exists()
    assert not sidecar.exists()
    assert destination.read_text() == "raw"
    assert destination.with_suffix(".xmp").read_text() == "xmp"


def test_apply_operations_real_and_dry_run_share_same_planned_behavior(
    tmp_path: Path,
) -> None:
    source_dry = tmp_path / "dry.jpg"
    source_dry.write_text("image-data")
    source_real = tmp_path / "real.jpg"
    source_real.write_text("image-data")

    destination_dry = tmp_path / "out" / "2020" / "01" / "02" / "dry.jpg"
    destination_real = tmp_path / "out" / "2020" / "01" / "02" / "real.jpg"

    dry_logs = apply_operations(
        [FileOperation(source=source_dry, destination=destination_dry, mode="move")],
        dry_run=True,
    )
    real_logs = apply_operations(
        [FileOperation(source=source_real, destination=destination_real, mode="move")],
        dry_run=False,
    )

    dry_suffix = dry_logs[0].split("] ", maxsplit=1)[1].replace(str(source_dry), "<SRC>").replace(
        str(destination_dry), "<DST>"
    )
    real_suffix = real_logs[0].split("] ", maxsplit=1)[1].replace(
        str(source_real), "<SRC>"
    ).replace(str(destination_real), "<DST>")

    assert dry_suffix == real_suffix
    assert source_dry.exists()
    assert not destination_dry.exists()
    assert not source_real.exists()
    assert destination_real.exists()


def test_plan_organization_operations_builds_operations_for_found_images(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"

    first_image = source_dir / "a.jpg"
    second_image = source_dir / "b.jpeg"
    first_image.write_text("a")
    second_image.write_text("b")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [first_image, second_image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    operations = plan_organization_operations(source_dir, output_dir, mode="move")

    assert len(operations) == 2
    assert operations[0].source == first_image
    assert operations[0].destination == output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    assert operations[0].mode == "move"
    assert operations[0].location is None
    assert operations[0].location_status == "disabled"


def test_plan_organization_operations_resolves_location_when_enabled(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")
    coordinates = GPSCoordinates(latitude=-23.5, longitude=-46.625)
    location = ReverseGeocodedLocation(
        city="Sao Paulo",
        state="Sao Paulo",
        country="Brazil",
    )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: coordinates,
    )
    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        lambda value: location if value == coordinates else None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        reverse_geocode=True,
    )

    assert operations[0].location == location
    assert operations[0].location_status == "resolved"


def test_plan_organization_operations_records_text_normalization(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "Cafe\u0301:01.jpg"
    image.write_text("a")
    coordinates = GPSCoordinates(latitude=-23.5, longitude=-46.625)
    location = ReverseGeocodedLocation(
        city="SÃ£o Paulo",
        state="SP",
        country="Brasil",
    )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: coordinates,
    )
    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        lambda _coordinates: location,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        reverse_geocode=True,
        organization_strategy="city-state-month",
        naming_pattern="{stem}{ext}",
    )

    assert operations[0].destination == (
        output_dir / "São Paulo-SP" / "2024-08" / "Café-01.jpg"
    )
    assert operations[0].location == ReverseGeocodedLocation(
        city="São Paulo",
        state="SP",
        country="Brasil",
    )
    assert any(
        observation.startswith("city: repaired legacy charset mojibake")
        for observation in operations[0].text_normalization_observations
    )
    assert any(
        "filename: normalized Unicode to NFC" in observation
        for observation in operations[0].text_normalization_observations
    )


def test_plan_organization_operations_uses_extracted_gps_for_reverse_geocoding(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "gps.jpg"
    image.write_text("gps")
    coordinates = GPSCoordinates(latitude=-23.5, longitude=-46.625)
    location = ReverseGeocodedLocation(
        city="Sao Paulo",
        state="Sao Paulo",
        country="Brazil",
    )
    geocoded_coordinates = []

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda path: coordinates if path == image else None,
    )

    def fake_reverse_geocode(value: GPSCoordinates):
        geocoded_coordinates.append(value)
        return location

    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        fake_reverse_geocode,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        reverse_geocode=True,
    )

    assert geocoded_coordinates == [coordinates]
    assert operations[0].coordinates == coordinates
    assert operations[0].location == location
    assert operations[0].location_status == "resolved"


def test_plan_organization_operations_uses_location_destination_when_selected(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")
    coordinates = GPSCoordinates(latitude=-23.5, longitude=-46.625)
    location = ReverseGeocodedLocation(
        city="Sao Paulo",
        state="Sao Paulo",
        country="Brazil",
    )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: coordinates,
    )
    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        lambda value: location if value == coordinates else None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        organization_strategy="location",
    )

    assert operations[0].destination == (
        output_dir / "Brazil" / "Sao Paulo" / "Sao Paulo" / "2024-08-15_14-32-09.jpg"
    )
    assert operations[0].organization_fallback is False


def test_plan_organization_operations_uses_location_date_destination_when_selected(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")
    coordinates = GPSCoordinates(latitude=-23.2, longitude=-44.7)
    location = ReverseGeocodedLocation(
        city="Paraty",
        state="RJ",
        country="Brasil",
    )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: coordinates,
    )
    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        lambda value: location if value == coordinates else None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        organization_strategy="location-date",
    )

    assert operations[0].destination == (
        output_dir
        / "Brasil"
        / "RJ"
        / "Paraty"
        / "2024"
        / "08"
        / "2024-08-15_14-32-09.jpg"
    )
    assert operations[0].organization_fallback is False


def test_plan_organization_operations_uses_city_state_month_destination_when_selected(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")
    coordinates = GPSCoordinates(latitude=-23.2, longitude=-44.7)
    location = ReverseGeocodedLocation(
        city="Paraty",
        state="RJ",
        country="Brasil",
    )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: coordinates,
    )
    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        lambda value: location if value == coordinates else None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        organization_strategy="city-state-month",
    )

    assert operations[0].destination == (
        output_dir / "Paraty-RJ" / "2024-08" / "2024-08-15_14-32-09.jpg"
    )
    assert operations[0].location == location
    assert operations[0].location_status == "resolved"
    assert operations[0].organization_fallback is False


def test_plan_organization_operations_falls_back_to_date_without_location(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.png"
    image.write_text("a")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        organization_strategy="location",
    )

    assert operations[0].destination == (
        output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.png"
    )
    assert operations[0].location_status == "missing-gps"
    assert operations[0].organization_fallback is True


def test_plan_organization_operations_location_date_falls_back_to_date_without_location(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        organization_strategy="location-date",
    )

    assert operations[0].destination == (
        output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )
    assert operations[0].location_status == "missing-gps"
    assert operations[0].organization_fallback is True


def test_plan_organization_operations_city_state_month_falls_back_without_location(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        organization_strategy="city-state-month",
    )

    assert operations[0].destination == (
        output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )
    assert operations[0].location_status == "missing-gps"
    assert operations[0].organization_fallback is True


def test_plan_organization_operations_uses_iptc_location_without_gps(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "legacy.jpg"
    image.write_bytes(
        _iptc_dataset(2, 90, "Paraty")
        + _iptc_dataset(2, 95, "RJ")
        + _iptc_dataset(2, 101, "Brasil")
    )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="city-state-month",
    )

    assert operations[0].location == ReverseGeocodedLocation(
        city="Paraty",
        state="RJ",
        country="Brasil",
    )
    assert operations[0].location_status == "inferred"
    assert operations[0].location_kind == "inferred"
    assert operations[0].location_provenance is not None
    assert operations[0].location_provenance.source == "IPTC-IIM"
    assert operations[0].location_provenance.field == "2:90,2:95,2:101"
    assert operations[0].destination == (
        output_dir / "Paraty-RJ" / "2024-08" / "2024-08-15_14-32-09.jpg"
    )


def test_plan_organization_operations_infers_xmp_textual_location_without_gps(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "xmp.jpg"
    image.write_bytes(
        b"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
      xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
      photoshop:City="Paraty"
      photoshop:State="RJ"
      photoshop:Country="Brasil" />
  </rdf:RDF>
</x:xmpmeta>"""
    )
    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="city-state-month",
    )

    assert operations[0].coordinates is None
    assert operations[0].location_status == "inferred"
    assert operations[0].location_kind == "inferred"
    assert operations[0].location_provenance is not None
    assert operations[0].location_provenance.source == "XMP"
    assert operations[0].destination == (
        output_dir / "Paraty-RJ" / "2024-08" / "2024-08-15_14-32-09.jpg"
    )


def test_plan_organization_operations_infers_location_from_manifest_without_gps(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "manifest.jpg"
    image.write_text("a")
    image.with_suffix(".location.json").write_text(
        '{"location": {"city": "Paraty", "state": "RJ", "country": "Brasil"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="city-state-month",
    )

    assert operations[0].location_status == "inferred"
    assert operations[0].location_provenance is not None
    assert operations[0].location_provenance.source == "External manifest"


def test_plan_organization_operations_applies_batch_correction_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "legacy_001.jpg"
    image.write_text("a")
    manifest_path = tmp_path / "corrections.json"
    correction_manifest = CorrectionManifest(
        path=manifest_path,
        rules=(
            CorrectionRule(
                selector="legacy_*.jpg",
                selector_type="glob",
                date_value="1969-07-20T20:17:00",
                city="Houston",
                state="TX",
                country="USA",
                event_name="Moon landing",
                priority="highest",
            ),
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )
    monkeypatch.setattr("photo_organizer.metadata.extract_xmp_metadata", lambda _path: {})
    monkeypatch.setattr(
        "photo_organizer.metadata.extract_iptc_iim_metadata",
        lambda _path: {},
    )
    monkeypatch.setattr("photo_organizer.metadata.extract_png_metadata", lambda _path: {})
    monkeypatch.setattr(
        "photo_organizer.metadata._read_exif_datetime_fields",
        lambda _path: {},
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="city-state-month",
        correction_manifest=correction_manifest,
    )

    assert operations[0].destination == (
        output_dir / "Houston-TX" / "1969-07" / "1969-07-20_20-17-00.jpg"
    )
    assert operations[0].location_status == "inferred"
    assert operations[0].location_provenance is not None
    assert operations[0].location_provenance.source == "Correction manifest"
    assert operations[0].date_provenance is not None
    assert operations[0].date_provenance.source == "Correction manifest"
    assert operations[0].correction_manifest is not None
    assert operations[0].correction_manifest.event_name == "Moon landing"


def test_plan_organization_operations_infers_location_from_folder_without_gps(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "Paraty-RJ"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")
    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="city-state-month",
    )

    assert operations[0].location == ReverseGeocodedLocation(
        city="Paraty",
        state="RJ",
        country=None,
    )
    assert operations[0].location_status == "inferred"
    assert operations[0].location_provenance is not None
    assert operations[0].location_provenance.source == "Folder"


def test_plan_organization_operations_infers_location_from_batch_without_gps(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    sibling = source_dir / "sibling.jpg"
    sibling.write_text("sibling")
    sibling.with_suffix(".location.json").write_text(
        '{"city": "Paraty", "state": "RJ", "country": "Brasil"}',
        encoding="utf-8",
    )
    image = source_dir / "a.jpg"
    image.write_text("a")
    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="city-state-month",
    )

    assert operations[0].coordinates is None
    assert operations[0].location_status == "inferred"
    assert operations[0].location_provenance is not None
    assert operations[0].location_provenance.source == "Batch"


def test_plan_organization_operations_uses_unknown_location_when_inference_disabled(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_bytes(
        _iptc_dataset(2, 90, "Paraty")
        + _iptc_dataset(2, 95, "RJ")
        + _iptc_dataset(2, 101, "Brasil")
    )
    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="city-state-month",
        location_inference=False,
    )

    assert operations[0].coordinates is None
    assert operations[0].location_status == "unknown-location"
    assert operations[0].location_kind == "unknown"
    assert operations[0].destination == (
        output_dir / "UnknownLocation" / "2024-08" / "2024-08-15_14-32-09.jpg"
    )


def test_plan_organization_operations_does_not_read_gps_when_geocoding_disabled(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )

    def fail_if_called(_path):
        raise AssertionError("GPS must not be read when reverse geocoding is disabled")

    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        fail_if_called,
    )

    operations = plan_organization_operations(source_dir, output_dir, mode="move")

    assert operations[0].location is None
    assert operations[0].location_status == "disabled"


def test_plan_organization_operations_marks_missing_gps_when_enabled(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.png"
    image.write_text("a")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: None,
    )

    def fail_if_called(_coordinates):
        raise AssertionError("reverse geocoding must not be called without GPS")

    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        fail_if_called,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="move",
        reverse_geocode=True,
    )

    assert operations[0].location is None
    assert operations[0].location_status == "missing-gps"


def test_plan_organization_operations_falls_back_to_date_when_location_unresolved(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "unresolved.jpg"
    image.write_text("gps")
    coordinates = GPSCoordinates(latitude=-23.5, longitude=-46.625)

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        lambda _p: DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_gps_coordinates",
        lambda _path: coordinates,
    )
    monkeypatch.setattr(
        "photo_organizer.executor.reverse_geocode_coordinates",
        lambda _coordinates: None,
    )

    operations = plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        organization_strategy="location",
    )

    assert operations[0].coordinates == coordinates
    assert operations[0].location is None
    assert operations[0].location_status == "unresolved"
    assert operations[0].organization_fallback is True
    assert operations[0].destination == (
        output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )


def test_plan_organization_operations_continues_after_bad_file(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    bad_image = source_dir / "bad.jpg"
    good_image = source_dir / "good.jpg"
    bad_image.write_text("bad")
    good_image.write_text("good")

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [bad_image, good_image],
    )

    def resolve_or_fail(path: Path) -> DateTimeResolution:
        if path == bad_image:
            raise ValueError("malformed metadata")
        return DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        )

    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        resolve_or_fail,
    )

    with caplog.at_level(logging.ERROR):
        operations = plan_organization_operations(source_dir, output_dir, mode="move")

    assert len(operations) == 1
    assert operations[0].source == good_image
    assert "Failed to plan file operation" in caplog.text
    assert str(bad_image) in caplog.text
    assert "malformed metadata" in caplog.text


def test_apply_operations_logs_errors_with_context(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    source = tmp_path / "input.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "input.jpg"

    def raise_copy(_src, _dst):
        raise OSError("permission denied")

    monkeypatch.setattr("photo_organizer.executor.shutil.copy2", raise_copy)

    with caplog.at_level(logging.ERROR):
        logs = apply_operations(
            [FileOperation(source=source, destination=destination, mode="move")],
            dry_run=False,
        )

    assert "Failed to execute operation: action=MOVE" in caplog.text
    assert str(source) in caplog.text
    assert str(destination) in caplog.text
    assert logs[0].startswith("[ERROR] MOVE")
    assert source.exists()
    assert not destination.exists()


def test_apply_operations_move_removes_source_after_success(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    expected_mtime = datetime(2024, 2, 3, 4, 5, 6).timestamp()
    os.utime(source, (expected_mtime, expected_mtime))

    destination = tmp_path / "out" / "source.jpg"
    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=False,
    )

    assert not source.exists()
    assert destination.exists()
    assert destination.read_text() == "image-data"
    assert destination.stat().st_mtime == expected_mtime
    assert logs == [f"[INFO] MOVE {source} -> {destination}"]


def test_apply_operations_move_creates_missing_destination_directories(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "source.jpg"

    assert not destination.parent.exists()

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=False,
    )

    assert destination.parent.is_dir()
    assert destination.exists()
    assert not source.exists()
    assert logs == [f"[INFO] MOVE {source} -> {destination}"]


def test_apply_operations_copy_creates_missing_destination_directories(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "source.jpg"

    assert not destination.parent.exists()

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.parent.is_dir()
    assert destination.exists()
    assert source.exists()
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_generates_heic_preview_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source.heic"
    source.write_text("image-data")
    destination = tmp_path / "out" / "source.heic"
    generated = {}

    def fake_generate(source_path, preview_path):
        generated["source"] = source_path
        generated["preview"] = preview_path
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text("preview")
        return preview_path

    monkeypatch.setattr("photo_organizer.executor.generate_heic_preview", fake_generate)

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
        heic_preview=True,
    )

    assert destination.exists()
    assert generated["source"] == destination
    assert generated["preview"] == tmp_path / "out" / ".previews" / "source.jpg"
    assert generated["preview"].read_text() == "preview"
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_keeps_success_when_heic_preview_fails(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    source = tmp_path / "source.heic"
    source.write_text("image-data")
    destination = tmp_path / "out" / "source.heic"

    def raise_preview(_source_path, _preview_path):
        raise RuntimeError("decoder unavailable")

    monkeypatch.setattr("photo_organizer.executor.generate_heic_preview", raise_preview)

    with caplog.at_level(logging.WARNING):
        logs = apply_operations(
            [FileOperation(source=source, destination=destination, mode="copy")],
            dry_run=False,
            heic_preview=True,
        )

    assert destination.exists()
    assert source.exists()
    assert "decoder unavailable" in caplog.text
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_is_idempotent_when_destination_directory_exists(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "2024" / "08" / "15" / "source.jpg"
    destination.parent.mkdir(parents=True)

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.parent.is_dir()
    assert destination.exists()
    assert source.exists()
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_move_keeps_source_when_removal_fails(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    destination = tmp_path / "out" / "source.jpg"

    original_unlink = Path.unlink

    def raise_for_source(path: Path, *args, **kwargs):
        if path == source:
            raise OSError("cannot remove source")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", raise_for_source)

    with caplog.at_level(logging.ERROR):
        logs = apply_operations(
            [FileOperation(source=source, destination=destination, mode="move")],
            dry_run=False,
        )

    assert source.exists()
    assert not destination.exists()
    assert "cannot remove source" in caplog.text
    assert logs[0].startswith(f"[ERROR] MOVE {source} -> {destination}")


def test_apply_operations_copy_preserves_basic_metadata_when_possible(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("image-data")
    expected_mtime = datetime(2024, 2, 3, 4, 5, 6).timestamp()
    os.utime(source, (expected_mtime, expected_mtime))

    destination = tmp_path / "out" / "source.jpg"
    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert source.exists()
    assert destination.exists()
    assert destination.read_text() == "image-data"
    assert destination.stat().st_mtime == source.stat().st_mtime
    assert logs == [f"[INFO] COPY {source} -> {destination}"]


def test_apply_operations_copy_uses_suffix_when_destination_exists(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")

    suffixed_destination = tmp_path / "out" / "source_01.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-data"
    assert suffixed_destination.read_text() == "new-data"
    assert source.exists()
    assert logs == [f"[INFO] COPY {source} -> {suffixed_destination}"]


def test_apply_operations_move_uses_suffix_when_destination_exists(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")

    suffixed_destination = tmp_path / "out" / "source_01.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="move")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-data"
    assert suffixed_destination.read_text() == "new-data"
    assert not source.exists()
    assert logs == [f"[INFO] MOVE {source} -> {suffixed_destination}"]


def test_apply_operations_uses_next_available_suffix_predictably(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    first_collision = tmp_path / "out" / "source_01.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")
    first_collision.write_text("also-existing")

    second_suffix = tmp_path / "out" / "source_02.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-data"
    assert first_collision.read_text() == "also-existing"
    assert second_suffix.read_text() == "new-data"
    assert logs == [f"[INFO] COPY {source} -> {second_suffix}"]


def test_apply_operations_uses_third_suffix_without_overwriting_existing_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    first_collision = tmp_path / "out" / "source_01.jpg"
    second_collision = tmp_path / "out" / "source_02.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-base")
    first_collision.write_text("existing-01")
    second_collision.write_text("existing-02")

    third_suffix = tmp_path / "out" / "source_03.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        dry_run=False,
    )

    assert destination.read_text() == "existing-base"
    assert first_collision.read_text() == "existing-01"
    assert second_collision.read_text() == "existing-02"
    assert third_suffix.read_text() == "new-data"
    assert logs == [f"[INFO] COPY {source} -> {third_suffix}"]


def test_apply_operations_skips_destination_conflict_when_configured(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        conflict_policy="skip",
    )

    assert source.exists()
    assert destination.read_text() == "existing-data"
    assert logs == [
        f"[SKIP] COPY {source} -> {destination} (conflict: destination exists)"
    ]


def test_apply_operations_overwrite_never_reports_conflict_error(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        conflict_policy="overwrite-never",
    )

    assert source.exists()
    assert destination.read_text() == "existing-data"
    assert logs == [
        f"[ERROR] COPY {source} -> {destination} "
        "(error: destination conflict; overwrite-never policy)"
    ]


def test_apply_operations_quarantines_destination_conflict(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")
    quarantine_dir = tmp_path / "quarantine"

    logs = apply_operations(
        [FileOperation(source=source, destination=destination, mode="copy")],
        conflict_policy="quarantine",
        conflict_quarantine_dir=quarantine_dir,
    )

    quarantined = quarantine_dir / "source.jpg"
    assert source.exists()
    assert destination.read_text() == "existing-data"
    assert quarantined.read_text() == "new-data"
    assert quarantined.with_suffix(".jpg.quarantine.json").exists()
    assert logs == [f"[INFO] QUARANTINE {source} -> {quarantined}"]


def test_apply_operations_fail_fast_raises_on_destination_conflict(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    source.write_text("new-data")
    destination = tmp_path / "out" / "source.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing-data")

    with pytest.raises(DestinationConflictError, match="Destination conflict"):
        apply_operations(
            [FileOperation(source=source, destination=destination, mode="copy")],
            conflict_policy="fail-fast",
        )

    assert destination.read_text() == "existing-data"


def test_apply_operations_dry_run_reserves_destinations_for_same_batch(
    tmp_path: Path,
) -> None:
    first_source = tmp_path / "first.jpg"
    second_source = tmp_path / "second.jpg"
    first_source.write_text("first")
    second_source.write_text("second")
    destination = tmp_path / "out" / "same.jpg"
    suffixed_destination = tmp_path / "out" / "same_01.jpg"

    logs = apply_operations(
        [
            FileOperation(source=first_source, destination=destination, mode="copy"),
            FileOperation(source=second_source, destination=destination, mode="copy"),
        ],
        dry_run=True,
    )

    assert logs == [
        f"[DRY-RUN] COPY {first_source} -> {destination}",
        f"[DRY-RUN] COPY {second_source} -> {suffixed_destination}",
    ]
    assert not destination.exists()
    assert not suffixed_destination.exists()


def test_apply_operations_reports_success_and_failure_per_item(tmp_path: Path) -> None:
    good_source = tmp_path / "good.jpg"
    good_source.write_text("ok")
    bad_source = tmp_path / "missing.jpg"

    good_destination = tmp_path / "out" / "good.jpg"
    bad_destination = tmp_path / "out" / "missing.jpg"

    logs = apply_operations(
        [
            FileOperation(source=good_source, destination=good_destination, mode="copy"),
            FileOperation(source=bad_source, destination=bad_destination, mode="copy"),
        ],
        dry_run=False,
    )

    assert good_destination.exists()
    assert len(logs) == 2
    assert logs[0] == f"[INFO] COPY {good_source} -> {good_destination}"
    assert logs[1].startswith(f"[ERROR] COPY {bad_source} -> {bad_destination}")


# ---------------------------------------------------------------------------
# Global clock_offset parameter
# ---------------------------------------------------------------------------

def test_plan_organization_operations_applies_global_clock_offset(
    tmp_path: Path, monkeypatch
) -> None:
    """A global clock_offset is injected as a synthetic CorrectionApplication."""
    from photo_organizer.correction_manifest import CorrectionApplication

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")

    captured_corrections: list = []

    def fake_resolve(path, **kwargs):
        captured_corrections.append(kwargs.get("correction"))
        return DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        fake_resolve,
    )

    plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        clock_offset="+3h",
    )

    assert len(captured_corrections) == 1
    correction = captured_corrections[0]
    assert isinstance(correction, CorrectionApplication)
    assert correction.clock_offset == "+3h"
    assert "global:clock_offset" in correction.selectors


def test_plan_organization_operations_global_clock_offset_does_not_override_manifest_offset(
    tmp_path: Path, monkeypatch
) -> None:
    """Per-file manifest clock_offset takes precedence over the global one."""
    from photo_organizer.correction_manifest import (
        CorrectionApplication,
        CorrectionManifest,
        CorrectionRule,
    )

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")

    manifest_path = tmp_path / "corrections.json"
    manifest = CorrectionManifest(
        path=manifest_path,
        rules=(
            CorrectionRule(
                selector="*.jpg",
                selector_type="glob",
                clock_offset="+01:00",
            ),
        ),
    )

    captured_corrections: list = []

    def fake_resolve(path, **kwargs):
        captured_corrections.append(kwargs.get("correction"))
        return DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        fake_resolve,
    )

    plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        correction_manifest=manifest,
        clock_offset="+3h",
    )

    assert len(captured_corrections) == 1
    correction = captured_corrections[0]
    # The manifest's per-file offset (+01:00) must be preserved.
    assert correction.clock_offset == "+01:00"


def test_plan_organization_operations_applies_camera_profile_clock_offset(
    tmp_path: Path, monkeypatch
) -> None:
    """Camera-profile manifest rules match EXIF make/model metadata."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    image = source_dir / "a.jpg"
    image.write_text("a")
    manifest = CorrectionManifest(
        path=tmp_path / "corrections.json",
        rules=(
            CorrectionRule(
                selector="Canon PowerShot A530",
                selector_type="camera",
                clock_offset="+3h",
            ),
        ),
    )
    captured_corrections: list = []

    def fake_resolve(path, **kwargs):
        captured_corrections.append(kwargs.get("correction"))
        return DateTimeResolution(
            value=datetime(2024, 8, 15, 14, 32, 9),
            used_fallback=False,
        )

    monkeypatch.setattr(
        "photo_organizer.executor.find_image_files",
        lambda _src, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.executor.extract_camera_profile",
        lambda _path: {
            "make": "Canon",
            "model": "PowerShot A530",
            "profile": "Canon PowerShot A530",
        },
    )
    monkeypatch.setattr(
        "photo_organizer.executor.resolve_best_available_datetime",
        fake_resolve,
    )

    plan_organization_operations(
        source_dir,
        output_dir,
        mode="copy",
        correction_manifest=manifest,
    )

    assert len(captured_corrections) == 1
    correction = captured_corrections[0]
    assert correction is not None
    assert correction.clock_offset == "+3h"
    assert correction.selectors == ("camera:Canon PowerShot A530",)


# ---------------------------------------------------------------------------
# Staging directory
# ---------------------------------------------------------------------------

def test_apply_operations_staging_copies_to_staging_then_promotes(
    tmp_path: Path,
) -> None:
    """Files are written to staging first, then promoted to final destination."""
    source = tmp_path / "source" / "a.jpg"
    source.parent.mkdir()
    source.write_text("image-data")

    output_dir = tmp_path / "output"
    staging_dir = tmp_path / "staging"
    final_dest = output_dir / "2024" / "08" / "15" / "a.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=final_dest, mode="copy")],
        staging_dir=staging_dir,
    )

    # Final destination must exist with correct content.
    assert final_dest.exists()
    assert final_dest.read_text() == "image-data"
    # Source must still exist (copy mode).
    assert source.exists()
    # Staging dir must be cleaned up after promotion.
    assert not staging_dir.exists()
    # Log must show INFO (success), not STAGED.
    assert len(logs) == 1
    assert logs[0].startswith("[INFO]")
    assert str(source) in logs[0]
    assert str(final_dest) in logs[0]


def test_apply_operations_staging_move_removes_source_after_promotion(
    tmp_path: Path,
) -> None:
    """In move mode the source is removed only after successful promotion."""
    source = tmp_path / "source" / "a.jpg"
    source.parent.mkdir()
    source.write_text("image-data")

    output_dir = tmp_path / "output"
    staging_dir = tmp_path / "staging"
    final_dest = output_dir / "2024" / "08" / "15" / "a.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=final_dest, mode="move")],
        staging_dir=staging_dir,
    )

    assert final_dest.exists()
    assert final_dest.read_text() == "image-data"
    # Source must be gone after a successful staged move.
    assert not source.exists()
    assert not staging_dir.exists()
    assert logs[0].startswith("[INFO]")


def test_apply_operations_staging_failure_leaves_output_untouched(
    tmp_path: Path,
) -> None:
    """When a copy to staging fails the final output directory is not created."""
    # Use a non-existent source to trigger a failure.
    missing_source = tmp_path / "ghost.jpg"
    output_dir = tmp_path / "output"
    staging_dir = tmp_path / "staging"
    final_dest = output_dir / "2024" / "08" / "15" / "ghost.jpg"

    logs = apply_operations(
        [FileOperation(source=missing_source, destination=final_dest, mode="copy")],
        staging_dir=staging_dir,
    )

    # Final output must not exist.
    assert not final_dest.exists()
    assert not output_dir.exists()
    # Staging area must be cleaned up.
    assert not staging_dir.exists()
    # All log lines must be errors.
    assert all(line.startswith("[ERROR]") for line in logs)


def test_apply_operations_staging_partial_failure_leaves_output_untouched(
    tmp_path: Path,
) -> None:
    """If any file fails during staging, no files are promoted to output."""
    good_source = tmp_path / "source" / "good.jpg"
    good_source.parent.mkdir()
    good_source.write_text("good")
    missing_source = tmp_path / "source" / "bad.jpg"

    output_dir = tmp_path / "output"
    staging_dir = tmp_path / "staging"
    good_dest = output_dir / "2024" / "01" / "01" / "good.jpg"
    bad_dest = output_dir / "2024" / "01" / "01" / "bad.jpg"

    logs = apply_operations(
        [
            FileOperation(source=good_source, destination=good_dest, mode="copy"),
            FileOperation(source=missing_source, destination=bad_dest, mode="copy"),
        ],
        staging_dir=staging_dir,
    )

    # Neither file must appear in the final output.
    assert not good_dest.exists()
    assert not bad_dest.exists()
    assert not output_dir.exists()
    # Staging area must be cleaned up.
    assert not staging_dir.exists()
    # All log lines must be errors.
    assert all(line.startswith("[ERROR]") for line in logs)
    assert len(logs) == 2


def test_apply_operations_staging_multiple_files_all_promoted(
    tmp_path: Path,
) -> None:
    """All files in a batch are promoted when every staging copy succeeds."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    files = []
    for name in ("a.jpg", "b.jpg", "c.png"):
        f = source_dir / name
        f.write_text(name)
        files.append(f)

    output_dir = tmp_path / "output"
    staging_dir = tmp_path / "staging"
    operations = [
        FileOperation(
            source=f,
            destination=output_dir / "2024" / "01" / f.name,
            mode="copy",
        )
        for f in files
    ]

    logs = apply_operations(operations, staging_dir=staging_dir)

    assert all(line.startswith("[INFO]") for line in logs)
    assert len(logs) == 3
    for f in files:
        assert (output_dir / "2024" / "01" / f.name).read_text() == f.name
    assert not staging_dir.exists()


def test_apply_operations_staging_dry_run_ignores_staging_dir(
    tmp_path: Path,
) -> None:
    """dry_run takes precedence over staging_dir; no files are written anywhere."""
    source = tmp_path / "a.jpg"
    source.write_text("x")
    staging_dir = tmp_path / "staging"
    final_dest = tmp_path / "output" / "a.jpg"

    logs = apply_operations(
        [FileOperation(source=source, destination=final_dest, mode="copy")],
        dry_run=True,
        staging_dir=staging_dir,
    )

    assert not final_dest.exists()
    assert not staging_dir.exists()
    assert logs[0].startswith("[DRY-RUN]")


def test_apply_operations_staging_cleans_up_on_success(
    tmp_path: Path,
) -> None:
    """The staging directory is removed after a successful run."""
    source = tmp_path / "a.jpg"
    source.write_text("x")
    staging_dir = tmp_path / "staging"
    final_dest = tmp_path / "output" / "a.jpg"

    apply_operations(
        [FileOperation(source=source, destination=final_dest, mode="copy")],
        staging_dir=staging_dir,
    )

    assert not staging_dir.exists()
