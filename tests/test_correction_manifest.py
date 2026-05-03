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
