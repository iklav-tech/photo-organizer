import json
from pathlib import Path

from photo_organizer.correction_manifest import (
    correction_for_file,
    load_correction_manifest,
)


def test_load_correction_manifest_matches_glob_and_merges_later_rules(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "corrections.json"
    manifest_path.write_text(
        json.dumps(
            {
                "priority": "metadata",
                "rules": [
                    {
                        "glob": "old/*.jpg",
                        "city": "Paraty",
                        "state": "RJ",
                        "event": "Archive",
                    },
                    {
                        "file": "old/a.jpg",
                        "date": "1969-07-20T20:17:00",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    source_root = tmp_path / "photos"
    source_root.mkdir()
    image = source_root / "old" / "a.jpg"
    image.parent.mkdir()
    image.write_text("x")

    manifest = load_correction_manifest(manifest_path)
    correction = correction_for_file(manifest, image, source_root)

    assert correction is not None
    assert correction.priority == "metadata"
    assert correction.date_value == "1969-07-20T20:17:00"
    assert correction.city == "Paraty"
    assert correction.state == "RJ"
    assert correction.event_name == "Archive"
    assert correction.selectors == ("glob:old/*.jpg", "file:old/a.jpg")


def test_load_correction_manifest_reads_csv_rules(tmp_path: Path) -> None:
    manifest_path = tmp_path / "corrections.csv"
    manifest_path.write_text(
        "glob,date,clock_offset,city,state,country\n"
        "*.jpg,1970-01-02T03:04:05,+01:30,Paraty,RJ,Brasil\n",
        encoding="utf-8",
    )
    image = tmp_path / "a.jpg"
    image.write_text("x")

    manifest = load_correction_manifest(manifest_path)
    correction = correction_for_file(manifest, image, tmp_path)

    assert correction is not None
    assert correction.date_value == "1970-01-02T03:04:05"
    assert correction.clock_offset == "+01:30"
    assert correction.location == {
        "city": "Paraty",
        "state": "RJ",
        "country": "Brasil",
    }


def test_correction_manifest_matches_camera_profile(tmp_path: Path) -> None:
    manifest_path = tmp_path / "corrections.json"
    manifest_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "camera": "Canon PowerShot A530",
                        "clock_offset": "+3h",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    image = tmp_path / "a.jpg"
    image.write_text("x")

    manifest = load_correction_manifest(manifest_path)
    correction = correction_for_file(
        manifest,
        image,
        tmp_path,
        camera_profile={
            "make": "Canon",
            "model": "PowerShot A530",
            "profile": "Canon PowerShot A530",
        },
    )

    assert correction is not None
    assert correction.clock_offset == "+3h"
    assert correction.selectors == ("camera:Canon PowerShot A530",)


def test_correction_manifest_matches_camera_make_and_model_fields(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "corrections.json"
    manifest_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "camera_make": "Olympus",
                        "camera_model": "C-2020Z",
                        "clock_offset": "-1d",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    image = tmp_path / "a.jpg"
    image.write_text("x")

    manifest = load_correction_manifest(manifest_path)
    correction = correction_for_file(
        manifest,
        image,
        tmp_path,
        camera_profile={
            "make": "Olympus",
            "model": "C-2020Z",
            "profile": "Olympus C-2020Z",
        },
    )

    assert correction is not None
    assert correction.clock_offset == "-1d"
    assert correction.selectors == ("camera_model:C-2020Z",)


def test_correction_manifest_matches_camera_model_selector(tmp_path: Path) -> None:
    manifest_path = tmp_path / "corrections.json"
    manifest_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "camera_model": "FinePix*",
                        "clock_offset": "+00:30",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    image = tmp_path / "a.jpg"
    image.write_text("x")

    manifest = load_correction_manifest(manifest_path)
    correction = correction_for_file(
        manifest,
        image,
        tmp_path,
        camera_profile={
            "make": "FUJIFILM",
            "model": "FinePix S5000",
            "profile": "FUJIFILM FinePix S5000",
        },
    )

    assert correction is not None
    assert correction.clock_offset == "+00:30"


def test_correction_manifest_matches_camera_make_only(tmp_path: Path) -> None:
    manifest_path = tmp_path / "corrections.json"
    manifest_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "camera_make": "Canon",
                        "clock_offset": "+1h",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    image = tmp_path / "a.jpg"
    image.write_text("x")

    manifest = load_correction_manifest(manifest_path)
    correction = correction_for_file(
        manifest,
        image,
        tmp_path,
        camera_profile={
            "make": "Canon",
            "model": "PowerShot A530",
            "profile": "Canon PowerShot A530",
        },
    )

    assert correction is not None
    assert correction.clock_offset == "+1h"
