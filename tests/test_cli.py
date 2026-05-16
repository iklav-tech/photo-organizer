import pytest
import csv
import hashlib
import json
from pathlib import Path
import logging
import os
from datetime import datetime

from photo_organizer.cli import main
import photo_organizer.cli as cli
from photo_organizer.correction_manifest import CorrectionApplication
from photo_organizer.executor import FileOperation
from photo_organizer.geocoding import ReverseGeocodedLocation
from photo_organizer.metadata import (
    GPSCoordinates,
    MetadataCandidate,
    MetadataProvenance,
    ReconciliationDecision,
)


def test_root_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "scan" in captured.out
    assert "dedupe" in captured.out
    assert "inspect" in captured.out
    assert "explain" in captured.out
    assert "organize" in captured.out
    assert "Examples:" in captured.out


def test_scan_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "SOURCE" in captured.out
    assert ".cr2" in captured.out
    assert ".nef" in captured.out
    assert ".dng" in captured.out
    assert ".heic" in captured.out
    assert ".heif" in captured.out
    assert "Examples:" in captured.out


def test_inspect_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "SOURCE" in captured.out
    assert "--report" in captured.out
    assert ".arw" in captured.out
    assert ".dng" in captured.out
    assert ".heic" in captured.out
    assert "Examples:" in captured.out


def test_dedupe_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["dedupe", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "SOURCE" in captured.out
    assert "--read-only" in captured.out
    assert "--report" in captured.out
    assert ".rw2" in captured.out
    assert "Examples:" in captured.out


def test_organize_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["organize", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "--output" in captured.out
    assert "--name-pattern" in captured.out
    assert "--dng-candidates" in captured.out
    assert "{date}" in captured.out
    assert "city-state-month" in captured.out
    assert ".orf" in captured.out
    assert ".raf" in captured.out
    assert ".heic" in captured.out
    assert "Paths:" in captured.out
    assert "Audit report:" in captured.out
    assert "Examples:" in captured.out


def test_organize_requires_output(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["organize", "./photos"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "organize requires --output DIR" in captured.err
    assert "photo-organizer organize ./Photos --output ./OrganizedPhotos" in captured.err


def test_organize_accepts_output_from_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "naming": {"pattern": "{date:%Y%m%d}_{stem}{ext}"},
                "destination": {"pattern": "{date:%Y}/{date:%m}"},
                "behavior": {
                    "mode": "copy",
                    "dry_run": True,
                    "reconciliation_policy": "filesystem",
                    "date_heuristics": False,
                    "location_inference": False,
                },
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_plan(*args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main(["organize", "./photos", "--config", str(config_path)])

    assert result == 0
    assert captured["args"][1] == str(tmp_path / "organized")
    assert captured["mode"] == "copy"
    assert captured["naming_pattern"] == "{date:%Y%m%d}_{stem}{ext}"
    assert captured["destination_pattern"] == "{date:%Y}/{date:%m}"
    assert captured["reconciliation_policy"] == "filesystem"
    assert captured["date_heuristics"] is False
    assert captured["location_inference"] is False


def test_organize_accepts_name_pattern_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--name-pattern",
        "{date:%Y%m%d}_{stem}{ext}",
    ])

    assert result == 0
    assert captured["naming_pattern"] == "{date:%Y%m%d}_{stem}{ext}"


def test_organize_accepts_heic_preview_from_cli(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: [],
    )

    def fake_apply(_operations, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--heic-preview",
    ])

    assert result == 0
    assert captured["heic_preview"] is True


def test_organize_accepts_heic_preview_from_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "preview": {"heic": True},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: [],
    )

    def fake_apply(_operations, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main(["organize", "./photos", "--config", str(config_path)])

    assert result == 0
    assert captured["heic_preview"] is True


def test_organize_accepts_dng_candidates_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--dng-candidates",
    ])

    assert result == 0
    assert captured["dng_candidates"] is True


def test_organize_accepts_dng_candidates_from_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "interop": {"dng_candidates": True},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main(["organize", "./photos", "--config", str(config_path)])

    assert result == 0
    assert captured["dng_candidates"] is True


def test_organize_accepts_derivative_segregation_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--segregate-derivatives",
        "--derived-path",
        "Working",
        "--derived-pattern",
        "*-proof",
    ])

    assert result == 0
    assert captured["segregate_derivatives"] is True
    assert captured["derivative_path"] == "Working"
    assert captured["derivative_patterns"] == ("*-proof",)


def test_organize_accepts_derivative_segregation_from_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "derivatives": {
                    "enabled": True,
                    "path": "Working",
                    "patterns": ["*-proof"],
                },
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main(["organize", "./photos", "--config", str(config_path)])

    assert result == 0
    assert captured["segregate_derivatives"] is True
    assert captured["derivative_path"] == "Working"
    assert captured["derivative_patterns"] == ("*-proof",)


def test_organize_accepts_reconciliation_policy_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--reconciliation-policy",
        "newest",
    ])

    assert result == 0
    assert captured["reconciliation_policy"] == "newest"


def test_organize_accepts_date_heuristics_toggle_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--no-date-heuristics",
    ])

    assert result == 0
    assert captured["date_heuristics"] is False


def test_organize_accepts_location_inference_toggle_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--no-location-inference",
    ])

    assert result == 0
    assert captured["location_inference"] is False


def test_organize_accepts_correction_manifest_from_cli(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_path = tmp_path / "corrections.json"
    manifest_path.write_text(
        json.dumps({"rules": [{"glob": "*.jpg", "date": "1969-07-20T20:17:00"}]}),
        encoding="utf-8",
    )
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--correction-manifest",
        str(manifest_path),
        "--correction-priority",
        "metadata",
    ])

    assert result == 0
    assert captured["correction_manifest"].path == manifest_path
    assert captured["correction_priority"] == "metadata"


def test_organize_name_pattern_cli_overrides_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": "./organized",
                "naming": {"pattern": "{date:%Y}_{stem}{ext}"},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--config",
        str(config_path),
        "--name-pattern",
        "{date:%Y%m%d}_{original}",
    ])

    assert result == 0
    assert captured["naming_pattern"] == "{date:%Y%m%d}_{original}"


def test_organize_rejects_invalid_name_pattern_from_cli(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([
            "organize",
            "./photos",
            "--output",
            "./organized",
            "--name-pattern",
            "{unknown}{ext}",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid --name-pattern" in captured.err
    assert "Unknown pattern field 'unknown'" in captured.err
    assert "Allowed: date, ext, original, stem" in captured.err


def test_organize_rejects_invalid_config(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"mode": "delete"}}),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        main(["organize", "./photos", "--config", str(config_path)])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid organize configuration" in captured.err
    assert "behavior.mode" in captured.err


def test_scan_requires_source(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "SOURCE" in captured.err


def test_organize_rejects_unknown_report_extension(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([
            "organize",
            "./photos",
            "--output",
            "./organized",
            "--report",
            "audit.txt",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "organize --report must end with .json or .csv" in captured.err
    assert "--report audit.csv" in captured.err


def test_dedupe_rejects_unknown_report_extension(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["dedupe", "./photos", "--report", "duplicates.txt"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "dedupe --report must end with .json or .csv" in captured.err
    assert "--report duplicates.json" in captured.err


def _inspect_item(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sources": [
            {
                "source": "EXIF",
                "exists": True,
                "fields": {"DateTimeOriginal": "2020:06:15 10:00:00"},
            }
        ],
        "date": {
            "decision": {
                "status": "resolved",
                "value": "2020-06-15T10:00:00",
                "source": "EXIF",
                "field": "DateTimeOriginal",
                "confidence": "high",
                "date_kind": "captured",
                "used_fallback": False,
                "reconciliation_policy": "precedence",
                "reconciliation_reason": "selected by metadata precedence policy",
                "conflict": False,
            },
            "candidates": [],
        },
        "location": {
            "decision": {
                "status": "inferred",
                "kind": "inferred",
                "latitude": None,
                "longitude": None,
                "city": "Paraty",
                "state": "RJ",
                "country": "Brasil",
                "provenance": {
                    "source": "External manifest",
                    "field": "a.json",
                    "confidence": "low",
                    "raw_value": {
                        "city": "Paraty",
                        "state": "RJ",
                        "country": "Brasil",
                    },
                },
            },
            "sources": [
                {
                    "source": "External manifest",
                    "exists": True,
                    "fields": {
                        "city": "Paraty",
                        "state": "RJ",
                        "country": "Brasil",
                    },
                }
            ],
        },
    }


def test_inspect_prints_sources_and_final_decisions(
    tmp_path: Path,
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image = tmp_path / "a.jpg"
    image.write_text("x")
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: _inspect_item(path),
    )

    result = main(["inspect", str(tmp_path)])

    assert result == 0
    captured = capsys.readouterr()
    assert f"File: {image}" in captured.out
    assert "Sources: EXIF" in captured.out
    assert "Date: resolved 2020-06-15T10:00:00" in captured.out
    assert "Location: inferred Paraty, RJ, Brasil" in captured.out


def test_inspect_prints_heif_container_complexity(
    tmp_path: Path,
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image = tmp_path / "a.heic"
    image.write_text("x")
    item = _inspect_item(image)
    item["sources"].append(  # type: ignore[index]
        {
            "source": "HEIF container",
            "exists": True,
            "fields": {
                "status": "complex",
                "image_count": 2,
                "selected_image_index": 1,
                "unsupported_features": [
                    "multiple images or sequence: only the selected primary image is processed",
                ],
            },
        }
    )
    item["heif"] = {
        "is_heif": True,
        "format": "HEIF/HEIC",
        "extension": ".heic",
        "container": {
            "status": "complex",
            "image_count": 2,
            "selected_image_index": 1,
            "unsupported_features": [
                "multiple images or sequence: only the selected primary image is processed",
            ],
        },
        "found_metadata": ["EXIF", "HEIF container"],
        "missing_metadata": ["XMP embedded", "XMP sidecar"],
        "date_evidence": {"kind": "real-metadata"},
        "location_evidence": {"kind": "inferred"},
    }
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: item,
    )

    result = main(["inspect", str(tmp_path)])

    assert result == 0
    captured = capsys.readouterr()
    assert "Sources: EXIF, HEIF container" in captured.out
    assert "HEIF: format=HEIF/HEIC status=complex images=2 selected_image=1" in captured.out
    assert "HEIF metadata: found=EXIF, HEIF container" in captured.out
    assert "missing=XMP embedded, XMP sidecar" in captured.out
    assert "HEIF evidence: date=real-metadata location=inferred" in captured.out
    assert "multiple images or sequence" in captured.out


def test_inspect_writes_json_report(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "a.jpg"
    image.write_text("x")
    report_path = tmp_path / "metadata-audit.json"
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: _inspect_item(path),
    )

    result = main(["inspect", str(tmp_path), "--report", str(report_path)])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {
        "inspected_files": 1,
        "date_resolved_files": 1,
        "location_resolved_files": 1,
        "date_conflict_files": 0,
    }
    assert report["files"][0]["date"]["decision"]["source"] == "EXIF"
    assert report["files"][0]["location"]["decision"]["city"] == "Paraty"


def test_inspect_report_includes_heif_audit_details(
    tmp_path: Path,
    monkeypatch,
) -> None:
    image = tmp_path / "a.heic"
    image.write_text("x")
    report_path = tmp_path / "metadata-audit.json"

    monkeypatch.setattr(
        "photo_organizer.cli.extract_exif_metadata",
        lambda _path: {"DateTimeOriginal": "2020:06:15 10:00:00"},
    )
    monkeypatch.setattr(
        "photo_organizer.cli.extract_embedded_xmp_metadata",
        lambda _path: {},
    )
    monkeypatch.setattr(
        "photo_organizer.cli.extract_xmp_sidecar_metadata",
        lambda _path: {},
    )
    monkeypatch.setattr(
        "photo_organizer.cli.extract_iptc_iim_metadata",
        lambda _path: {},
    )
    monkeypatch.setattr("photo_organizer.cli.extract_png_metadata", lambda _path: {})
    monkeypatch.setattr(
        "photo_organizer.cli.extract_heif_container_metadata",
        lambda _path: {
            "status": "supported",
            "mimetype": "image/heic",
            "image_count": 1,
            "selected_image_index": 0,
        },
    )
    monkeypatch.setattr("photo_organizer.cli.extract_camera_profile", lambda _path: {})
    monkeypatch.setattr(
        "photo_organizer.cli.resolve_best_available_datetime",
        lambda *_args, **_kwargs: type(
            "Resolution",
            (),
            {
                "value": datetime(2020, 6, 15, 10, 0, 0),
                "provenance": MetadataProvenance(
                    source="EXIF",
                    field="DateTimeOriginal",
                    confidence="high",
                    raw_value="2020:06:15 10:00:00",
                ),
                "date_kind": "captured",
                "used_fallback": False,
                "reconciliation": None,
            },
        )(),
    )
    monkeypatch.setattr("photo_organizer.cli.extract_gps_coordinates", lambda _path: None)
    monkeypatch.setattr(
        "photo_organizer.cli.extract_external_location_manifest",
        lambda _path: None,
    )
    monkeypatch.setattr("photo_organizer.cli.extract_xmp_textual_location", lambda _path: None)
    monkeypatch.setattr("photo_organizer.cli.extract_iptc_iim_location", lambda _path: None)
    monkeypatch.setattr("photo_organizer.cli.infer_location_from_folder", lambda _path: None)
    monkeypatch.setattr("photo_organizer.cli.infer_location_from_batch", lambda _path: None)

    result = main(["inspect", str(tmp_path), "--report", str(report_path)])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    audit = report["files"][0]["heif"]
    assert audit["format"] == "HEIF/HEIC"
    assert audit["container"]["status"] == "supported"
    assert audit["found_metadata"] == ["EXIF", "HEIF container"]
    assert audit["missing_metadata"] == ["XMP embedded", "XMP sidecar"]
    assert audit["date_evidence"]["kind"] == "real-metadata"
    assert audit["location_evidence"]["kind"] == "missing"


def test_inspect_report_includes_apple_proraw_raw_audit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    image = tmp_path / "a.dng"
    image.write_text("x")
    report_path = tmp_path / "metadata-audit.json"
    item = _inspect_item(image)
    item["raw"] = {
        "is_raw": True,
        "format": "Apple ProRAW",
        "extension": ".dng",
        "flow": "Apple ProRAW / Linear DNG",
        "status": "supported",
        "fields": {
            "make": {
                "status": "found",
                "value": "Apple",
                "source": "EXIF",
                "field": "Make",
                "confidence": "high",
                "raw_value": "Apple",
            }
        },
        "found_fields": ["make"],
        "missing_fields": [],
        "warnings": [],
    }

    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: item,
    )

    result = main(["inspect", str(tmp_path), "--report", str(report_path)])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    raw_audit = report["files"][0]["raw"]
    assert raw_audit["is_raw"] is True
    assert raw_audit["format"] == "Apple ProRAW"
    assert raw_audit["flow"] == "Apple ProRAW / Linear DNG"
    assert raw_audit["status"] == "supported"


def test_raw_audit_reports_field_origins_and_partial_support() -> None:
    path = Path("IMG_0001.dng")
    source_items = [
        {
            "source": "EXIF",
            "exists": True,
            "fields": {
                "Make": "Apple",
                "DateTimeOriginal": "2024:05:06 07:08:09",
                "GPSLatitude": [[23, 1], [30, 1], [0, 1]],
                "GPSLatitudeDecimal": -23.5,
                "GPSLatitudeRef": "S",
                "GPSLongitude": [[46, 1], [37, 1], [30, 1]],
                "GPSLongitudeDecimal": -46.625,
                "GPSLongitudeRef": "W",
            },
        }
    ]
    date_decision = {
        "status": "resolved",
        "value": "2024-05-07T07:08:09",
        "source": "Correction manifest",
        "field": "manual",
        "confidence": "high",
    }
    location_decision = {
        "status": "missing",
        "kind": "none",
        "latitude": None,
        "longitude": None,
        "provenance": None,
    }

    audit = cli._raw_audit_item(
        path,
        source_items,
        date_decision,
        location_decision,
    )

    assert audit is not None
    assert audit["format"] == "Apple ProRAW"
    assert audit["status"] == "partial"
    assert audit["found_fields"] == ["make", "datetime", "gps"]
    assert audit["missing_fields"] == ["model"]
    fields = audit["fields"]
    assert fields["make"]["source"] == "EXIF"
    assert fields["make"]["field"] == "Make"
    assert fields["datetime"]["field"] == "DateTimeOriginal"
    assert fields["datetime"]["value"] == "2024:05:06 07:08:09"
    assert fields["gps"]["field"] == "GPSLatitudeDecimal,GPSLongitudeDecimal"
    assert fields["gps"]["value"] == {"latitude": -23.5, "longitude": -46.625}
    assert "missing model" in audit["warnings"][0]


def test_inspect_prints_raw_metadata_and_warnings(
    tmp_path: Path,
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image = tmp_path / "a.dng"
    image.write_text("x")
    item = _inspect_item(image)
    item["raw"] = {
        "is_raw": True,
        "format": "Apple ProRAW",
        "extension": ".dng",
        "flow": "Apple ProRAW / Linear DNG",
        "status": "partial",
        "fields": {
            "make": {
                "status": "found",
                "value": "Apple",
                "source": "EXIF",
                "field": "Make",
                "confidence": "high",
                "raw_value": "Apple",
            },
            "model": {
                "status": "found",
                "value": "iPhone 15 Pro",
                "source": "EXIF",
                "field": "Model",
                "confidence": "high",
                "raw_value": "iPhone 15 Pro",
            },
            "datetime": {
                "status": "found",
                "value": "2024-05-06T07:08:09",
                "source": "EXIF",
                "field": "DateTimeOriginal",
                "confidence": "high",
                "raw_value": "2024:05:06 07:08:09",
            },
            "gps": {"status": "missing"},
        },
        "found_fields": ["make", "model", "datetime"],
        "missing_fields": ["gps"],
        "warnings": [
            "RAW metadata partially supported: missing gps from TIFF-style EXIF"
        ],
    }

    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: item,
    )

    result = main(["inspect", str(tmp_path)])

    assert result == 0
    captured = capsys.readouterr()
    assert "RAW: format=Apple ProRAW status=partial flow=Apple ProRAW / Linear DNG" in captured.out
    assert "make=Apple [EXIF:Make confidence=high]" in captured.out
    assert "model=iPhone 15 Pro [EXIF:Model confidence=high]" in captured.out
    assert "datetime=2024-05-06T07:08:09 [EXIF:DateTimeOriginal confidence=high]" in captured.out
    assert "gps=missing" in captured.out
    assert "RAW warning: RAW metadata partially supported: missing gps" in captured.out


def test_inspect_writes_csv_report(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "a.jpg"
    image.write_text("x")
    report_path = tmp_path / "metadata-audit.csv"
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: _inspect_item(path),
    )

    result = main(["audit-metadata", str(tmp_path), "--report", str(report_path)])

    assert result == 0
    with report_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.DictReader(report_file))
    assert rows[0]["path"] == str(image)
    assert rows[0]["sources"] == "EXIF"
    assert rows[0]["date_source"] == "EXIF"
    assert rows[0]["location_status"] == "inferred"


def test_inspect_accepts_heic_files_with_filesystem_fallback(tmp_path: Path) -> None:
    image = tmp_path / "IMG_0001.HEIC"
    image.write_bytes(b"heic-placeholder")
    expected_ts = datetime(2024, 5, 6, 7, 8, 9).timestamp()
    os.utime(image, (expected_ts, expected_ts))
    report_path = tmp_path / "metadata-audit.json"

    result = main(["inspect", str(tmp_path), "--report", str(report_path)])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["inspected_files"] == 1
    assert report["files"][0]["path"] == str(image)
    assert report["files"][0]["date"]["decision"]["source"] == "filesystem"
    assert report["files"][0]["heif"]["format"] == "HEIF/HEIC"
    assert report["files"][0]["heif"]["date_evidence"]["kind"] == "inferred-or-fallback"


def test_inspect_rejects_unknown_report_extension(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect", str(tmp_path), "--report", "metadata-audit.txt"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "inspect --report must end with .json or .csv" in captured.err


def test_explain_writes_json_decision_report(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "a.jpg"
    image.write_text("x")
    report_path = tmp_path / "explain.json"
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: _inspect_item(path),
    )

    result = main(["explain", str(tmp_path), "--report", str(report_path)])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {
        "explained_files": 1,
        "date_resolved_files": 1,
        "location_resolved_files": 1,
        "date_conflict_files": 0,
    }
    item = report["files"][0]
    assert item["chosen_date"]["value"] == "2020-06-15T10:00:00"
    assert item["chosen_date"]["source"] == "EXIF"
    assert item["chosen_date"]["confidence"] == "high"
    assert item["chosen_location"]["city"] == "Paraty"
    assert item["chosen_location"]["source"] == "External manifest"
    assert item["chosen_location"]["confidence"] == "low"
    assert "candidates" in item
    assert "date" in item["candidates"]
    assert item["candidates"]["location"][0]["source"] == "External manifest"


def test_explain_rejects_non_json_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["explain", str(tmp_path), "--report", "explain.csv"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "explain --report must end with .json" in captured.err


def test_explain_json_handles_non_json_exif_raw_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class RationalLike:
        def __float__(self) -> float:
            return 1.5

    image = tmp_path / "a.jpg"
    image.write_text("x")
    report_path = tmp_path / "explain.json"
    item = _inspect_item(image)
    item["date"]["candidates"] = [  # type: ignore[index]
        {
            "value": "2020-06-15T10:00:00",
            "source": "EXIF",
            "field": "GPSInfo",
            "confidence": "high",
            "raw_value": {"GPSLatitude": (RationalLike(), RationalLike())},
            "role": "primary",
            "date_kind": "captured",
            "used_fallback": False,
        }
    ]
    item["location"]["sources"][0]["raw_value"] = {  # type: ignore[index]
        "GPSLatitude": (RationalLike(), RationalLike()),
    }

    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [image],
    )
    monkeypatch.setattr(
        "photo_organizer.cli._inspect_file",
        lambda path, *_args, **_kwargs: item,
    )

    result = main(["explain", str(tmp_path), "--report", str(report_path)])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["files"][0]["candidates"]["date"][0]["raw_value"] == {
        "GPSLatitude": [1.5, 1.5],
    }
    assert report["files"][0]["candidates"]["location"][0]["raw_value"] == {
        "GPSLatitude": [1.5, 1.5],
    }


def test_inspect_location_reverse_geocodes_gps(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "a.jpg"
    image.write_text("x")
    coordinates = GPSCoordinates(
        latitude=-23.2,
        longitude=-44.7,
        provenance=MetadataProvenance(
            source="EXIF",
            field="GPSInfo",
            confidence="high",
            raw_value={"GPSLatitudeDecimal": -23.2, "GPSLongitudeDecimal": -44.7},
        ),
    )
    monkeypatch.setattr(
        "photo_organizer.cli.extract_gps_coordinates",
        lambda _path: coordinates,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.reverse_geocode_coordinates",
        lambda _coordinates: ReverseGeocodedLocation(
            city="Paraty",
            state="RJ",
            country="Brasil",
        ),
    )
    for resolver_name in (
        "extract_iptc_iim_location",
        "extract_xmp_textual_location",
        "extract_external_location_manifest",
        "infer_location_from_folder",
        "infer_location_from_batch",
    ):
        monkeypatch.setattr(f"photo_organizer.cli.{resolver_name}", lambda _path: None)

    decision, sources = cli._inspect_location(image, reverse_geocode=True)

    assert decision["status"] == "resolved"
    assert decision["city"] == "Paraty"
    assert sources[0]["source"] == "EXIF"


def test_organize_plan_mode_shows_plan_without_execution(
    monkeypatch, caplog
) -> None:
    planned = [
        FileOperation(
            source=Path("input/a.jpg"),
            destination=Path("out/2024/08/15/2024-08-15_14-32-09.jpg"),
            mode="move",
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("apply_operations must not be called in --plan mode")

    monkeypatch.setattr("photo_organizer.cli.apply_operations", fail_if_called)

    with caplog.at_level(logging.INFO):
        result = main(["organize", "./photos", "--output", "./organized", "--plan"])

    assert result == 0
    assert "Generated execution plan: operations=1" in caplog.text
    assert "Plan-only mode enabled" in caplog.text


def test_organize_reverse_geocode_option_is_passed_to_planner(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--reverse-geocode",
    ])

    assert result == 0
    assert captured["reverse_geocode"] is True
    assert captured["organization_strategy"] == "date"


def test_organize_location_strategy_enables_reverse_geocoding(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--by",
        "location",
    ])

    assert result == 0
    assert captured["reverse_geocode"] is True
    assert captured["organization_strategy"] == "location"


def test_organize_location_date_strategy_enables_reverse_geocoding(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--by",
        "location-date",
    ])

    assert result == 0
    assert captured["reverse_geocode"] is True
    assert captured["organization_strategy"] == "location-date"


def test_organize_city_state_month_strategy_enables_reverse_geocoding(
    monkeypatch,
) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--by",
        "city-state-month",
    ])

    assert result == 0
    assert captured["reverse_geocode"] is True
    assert captured["organization_strategy"] == "city-state-month"


def test_organize_location_strategy_rejects_disabled_geocoding(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([
            "organize",
            "./photos",
            "--output",
            "./organized",
            "--by",
            "location",
            "--no-reverse-geocode",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "--by location requires reverse geocoding" in captured.err


def test_organize_location_date_strategy_rejects_disabled_geocoding(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([
            "organize",
            "./photos",
            "--output",
            "./organized",
            "--by",
            "location-date",
            "--no-reverse-geocode",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "--by location-date requires reverse geocoding" in captured.err


def test_organize_city_state_month_strategy_rejects_disabled_geocoding(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([
            "organize",
            "./photos",
            "--output",
            "./organized",
            "--by",
            "city-state-month",
            "--no-reverse-geocode",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "--by city-state-month requires reverse geocoding" in captured.err


def test_scan_logs_start_end_and_count(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [Path("a.jpg"), Path("b.jpg")],
    )

    with caplog.at_level(logging.INFO):
        result = main(["scan", "./photos"])

    assert result == 0
    assert "Execution started: scan source=./photos" in caplog.text
    assert ".heic" in caplog.text
    assert "Execution finished: scan processed_files=2" in caplog.text


def test_scan_nonexistent_directory_returns_clear_message(caplog) -> None:
    with caplog.at_level(logging.INFO):
        result = main(["scan", "./does-not-exist"])

    assert result == 1
    assert "Source directory does not exist" in caplog.text
    assert "Execution finished: scan processed_files=0" in caplog.text


def test_dedupe_lists_duplicate_groups_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)
    original = source_dir / "a.jpg"
    duplicate = nested_dir / "b.png"
    different = source_dir / "c.jpg"
    original.write_bytes(b"same content")
    duplicate.write_bytes(b"same content")
    different.write_bytes(b"different content")

    result = main(["dedupe", str(source_dir), "--read-only"])

    assert result == 0
    captured = capsys.readouterr()
    assert "Duplicate group 1:" in captured.out
    assert "Hash:" in captured.out
    assert "Quantity: 2" in captured.out
    assert f"Original: {original}" in captured.out
    assert f"Duplicate: {duplicate}" in captured.out
    assert str(different) not in captured.out
    assert original.read_bytes() == b"same content"
    assert duplicate.read_bytes() == b"same content"
    assert different.read_bytes() == b"different content"


def test_dedupe_lists_all_duplicates_in_group(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    original = source_dir / "a.jpg"
    first_duplicate = source_dir / "b.jpg"
    second_duplicate = source_dir / "c.png"
    original.write_bytes(b"same content")
    first_duplicate.write_bytes(b"same content")
    second_duplicate.write_bytes(b"same content")

    result = main(["dedupe", str(source_dir)])

    assert result == 0
    captured = capsys.readouterr()
    assert "Duplicate group 1:" in captured.out
    assert "Quantity: 3" in captured.out
    assert f"Original: {original}" in captured.out
    assert f"Duplicate: {first_duplicate}" in captured.out
    assert f"Duplicate: {second_duplicate}" in captured.out


def test_dedupe_reports_no_duplicates_for_different_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    first = source_dir / "first.jpg"
    second = source_dir / "second.png"
    first.write_bytes(b"content one")
    second.write_bytes(b"content two")

    result = main(["dedupe", str(source_dir)])

    assert result == 0
    captured = capsys.readouterr()
    assert captured.out == "No duplicate images found.\n"


def test_dedupe_writes_structured_json_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    report_path = tmp_path / "reports" / "duplicates.json"
    source_dir.mkdir()
    original = source_dir / "a.jpg"
    duplicate = source_dir / "b.png"
    different = source_dir / "c.jpg"
    original.write_bytes(b"same content")
    duplicate.write_bytes(b"same content")
    different.write_bytes(b"different content")
    expected_hash = hashlib.sha256(b"same content").hexdigest()

    result = main(["dedupe", str(source_dir), "--report", str(report_path)])

    assert result == 0
    capsys.readouterr()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {
        "duplicate_groups": 1,
        "duplicate_files": 1,
        "total_files_in_duplicate_groups": 2,
    }
    assert report["duplicate_groups"] == [
        {
            "group_id": 1,
            "hash": expected_hash,
            "quantity": 2,
            "original": str(original),
            "duplicates": [str(duplicate)],
            "paths": [str(original), str(duplicate)],
        }
    ]


def test_dedupe_writes_analysis_friendly_csv_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "photos"
    report_path = tmp_path / "duplicates.csv"
    source_dir.mkdir()
    original = source_dir / "a.jpg"
    duplicate = source_dir / "b.jpg"
    original.write_bytes(b"same content")
    duplicate.write_bytes(b"same content")
    expected_hash = hashlib.sha256(b"same content").hexdigest()

    result = main(["dedupe", str(source_dir), "--report", str(report_path)])

    assert result == 0
    capsys.readouterr()
    with report_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.DictReader(report_file))

    assert rows == [
        {
            "group_id": "1",
            "hash": expected_hash,
            "quantity": "2",
            "role": "original",
            "path": str(original),
        },
        {
            "group_id": "1",
            "hash": expected_hash,
            "quantity": "2",
            "role": "duplicate",
            "path": str(duplicate),
        },
    ]


def test_dedupe_nonexistent_directory_returns_clear_message(caplog) -> None:
    with caplog.at_level(logging.INFO):
        result = main(["dedupe", "./does-not-exist"])

    assert result == 1
    assert "Source directory does not exist" in caplog.text
    assert "Execution finished: dedupe duplicate_groups=0 duplicate_files=0" in caplog.text


def test_log_level_can_be_adjusted(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "photo_organizer.cli.find_image_files",
        lambda _source, recursive=True: [],
    )

    with caplog.at_level(logging.DEBUG):
        result = main(["--log-level", "ERROR", "scan", "./photos"])

    assert result == 0
    assert "Execution started: scan" not in caplog.text


def test_organize_dry_run_end_to_end_shows_expected_destinations_and_keeps_files(
    tmp_path: Path, caplog
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source_dir.mkdir()

    first = source_dir / "IMG_1.jpg"
    second = source_dir / "IMG_2.png"
    ignored = source_dir / "notes.txt"
    first.write_text("a")
    second.write_text("b")
    ignored.write_text("ignore me")

    first_dt = (2024, 8, 15, 14, 32, 9)
    second_dt = (2023, 1, 2, 3, 4, 5)
    first_ts = datetime(*first_dt).timestamp()
    second_ts = datetime(*second_dt).timestamp()
    os.utime(first, (first_ts, first_ts))
    os.utime(second, (second_ts, second_ts))

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
            "--dry-run",
        ])

    assert result == 0

    first_expected = (
        output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    )
    second_expected = (
        output_dir / "2023" / "01" / "02" / "2023-01-02_03-04-05.png"
    )

    assert f"[DRY-RUN] MOVE {first} -> {first_expected}" in caplog.text
    assert f"[DRY-RUN] MOVE {second} -> {second_expected}" in caplog.text

    # Dry-run must not alter input files or create output files.
    assert first.exists()
    assert second.exists()
    assert ignored.exists()
    assert not first_expected.exists()
    assert not second_expected.exists()
    assert (
        "Execution summary: mode=dry-run processed_files=2 ignored_files=1 "
        "error_files=0 fallback_files=2 location_files=0 gps_files=0 "
        "missing_gps_files=0 "
        "organization_fallback_files=0"
    ) in caplog.text


def test_organize_dry_run_accepts_heic_files(tmp_path: Path, caplog) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source_dir.mkdir()
    image = source_dir / "IMG_0001.heic"
    image.write_bytes(b"heic-placeholder")
    expected_ts = datetime(2024, 5, 6, 7, 8, 9).timestamp()
    os.utime(image, (expected_ts, expected_ts))

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
            "--dry-run",
        ])

    expected = output_dir / "2024" / "05" / "06" / "2024-05-06_07-08-09.heic"
    assert result == 0
    assert f"[DRY-RUN] MOVE {image} -> {expected}" in caplog.text
    assert "processed_files=1" in caplog.text


def test_organize_end_to_end_adds_suffixes_for_destination_collisions(
    tmp_path: Path, caplog
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    source_dir.mkdir()

    first = source_dir / "2025-10-31_11-07-10 (Copia 2).png"
    second = source_dir / "2025-10-31_11-07-10 (Copia).png"
    third = source_dir / "2025-10-31_11-07-10.png"
    first.write_text("first")
    second.write_text("second")
    third.write_text("third")

    fallback_ts = datetime(2025, 10, 31, 11, 7, 10).timestamp()
    for source in [first, second, third]:
        os.utime(source, (fallback_ts, fallback_ts))

    expected_base = output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10.png"
    expected_first_suffix = (
        output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10_01.png"
    )
    expected_second_suffix = (
        output_dir / "2025" / "10" / "31" / "2025-10-31_11-07-10_02.png"
    )

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
        ])

    assert result == 0

    assert expected_base.read_text() == "first"
    assert expected_first_suffix.read_text() == "second"
    assert expected_second_suffix.read_text() == "third"
    assert not first.exists()
    assert not second.exists()
    assert not third.exists()

    assert f"MOVE {first} -> {expected_base}" in caplog.text
    assert f"MOVE {second} -> {expected_first_suffix}" in caplog.text
    assert f"MOVE {third} -> {expected_second_suffix}" in caplog.text
    assert (
        "Execution summary: mode=execute processed_files=3 ignored_files=0 "
        "error_files=0 fallback_files=3 location_files=0 gps_files=0 "
        "missing_gps_files=0 "
        "organization_fallback_files=0"
    ) in caplog.text


def test_organize_summary_counts_operation_errors(monkeypatch, caplog) -> None:
    planned = [
        FileOperation(
            source=Path("input/good.jpg"),
            destination=Path("out/good.jpg"),
            mode="copy",
            date_fallback=True,
        ),
        FileOperation(
            source=Path("input/bad.jpg"),
            destination=Path("out/bad.jpg"),
            mode="copy",
            date_fallback=False,
        ),
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/good.jpg -> out/good.jpg",
            "[ERROR] COPY input/bad.jpg -> out/bad.jpg (error: failed)",
        ],
    )

    with caplog.at_level(logging.INFO):
        result = main(["organize", "./photos", "--output", "./organized", "--copy"])

    assert result == 0
    assert (
        "Execution summary: mode=execute processed_files=1 ignored_files=0 "
        "error_files=1 fallback_files=1 location_files=0 gps_files=0 "
        "missing_gps_files=0 "
        "organization_fallback_files=0"
    ) in caplog.text


def test_organize_writes_valid_structured_execution_report(
    tmp_path: Path, caplog
) -> None:
    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    report_path = tmp_path / "reports" / "execution.json"
    source_dir.mkdir()

    source = source_dir / "IMG_1.jpg"
    source.write_text("image-data")
    expected_ts = datetime(2024, 8, 15, 14, 32, 9).timestamp()
    os.utime(source, (expected_ts, expected_ts))

    destination = output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
            "--copy",
            "--report",
            str(report_path),
        ])

    assert result == 0
    assert "Execution report written" in caplog.text

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {
        "mode": "execute",
        "processed_files": 1,
        "ignored_files": 0,
        "error_files": 0,
        "fallback_files": 1,
        "location_files": 0,
        "gps_files": 0,
        "missing_gps_files": 0,
        "organization_fallback_files": 0,
    }
    assert report["operations"] == [
        {
            "source": str(source),
            "destination": str(destination),
            "action": "copy",
            "status": "success",
            "observations": "",
            "date_source": "filesystem",
            "date_field": "mtime",
            "date_confidence": "low",
            "date_raw_value": json.dumps(expected_ts),
            "chosen_date": "2024-08-15T14:32:09",
            "chosen_location": "",
            "metadata_source": "filesystem:mtime",
            "conflict": False,
            "conflict_sources": "",
            "conflict_reason": "",
            "date_kind": "inferred",
            "event_name": "",
            "sidecar_count": 0,
            "sidecar_sources": "",
            "sidecar_destinations": "",
            "raw_family": False,
            "raw_format": "",
            "raw_flow": "",
            "asset_role": "original",
            "derived": False,
            "derived_reason": "",
            "dng_candidate": False,
            "dng_candidate_reason": "",
        }
    ]


def test_organize_report_includes_error_status_and_observation(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/bad.jpg"),
            destination=Path("out/bad.jpg"),
            mode="copy",
            date_fallback=False,
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[ERROR] COPY input/bad.jpg -> out/bad.jpg (error: permission denied)",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["error_files"] == 1
    assert report["operations"] == [
        {
            "source": "input/bad.jpg",
            "destination": "out/bad.jpg",
            "action": "copy",
            "status": "error",
            "observations": "permission denied",
            "date_source": "",
            "date_field": "",
            "date_confidence": "",
            "date_raw_value": "",
            "chosen_date": "",
            "chosen_location": "",
            "metadata_source": "",
            "conflict": False,
            "conflict_sources": "",
            "conflict_reason": "",
            "date_kind": "captured",
            "event_name": "",
            "sidecar_count": 0,
            "sidecar_sources": "",
            "sidecar_destinations": "",
            "raw_family": False,
            "raw_format": "",
            "raw_flow": "",
            "asset_role": "original",
            "derived": False,
            "derived_reason": "",
            "dng_candidate": False,
            "dng_candidate_reason": "",
        }
    ]


def test_organize_report_includes_linked_raw_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/IMG_0001.cr2"),
            destination=Path("out/2024-08-15_14-32-09.cr2"),
            mode="copy",
            related_sidecars=(Path("input/IMG_0001.xmp"),),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/IMG_0001.cr2 -> out/2024-08-15_14-32-09.cr2",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    operation = report["operations"][0]
    assert operation["sidecar_count"] == 1
    assert operation["sidecar_sources"] == "input/IMG_0001.xmp"
    assert operation["sidecar_destinations"] == "out/2024-08-15_14-32-09.xmp"
    assert operation["observations"] == (
        "linked sidecars: sources=input/IMG_0001.xmp; "
        "destinations=out/2024-08-15_14-32-09.xmp"
    )


def test_organize_report_includes_dng_candidate_marker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/IMG_0001.cr3"),
            destination=Path("out/2024-08-15_14-32-09.cr3"),
            mode="copy",
            dng_candidate=True,
            dng_candidate_reason=(
                "RAW file selected for optional DNG interoperability workflow"
            ),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/IMG_0001.cr3 -> out/2024-08-15_14-32-09.cr3",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    operation = report["operations"][0]
    assert operation["dng_candidate"] is True
    assert operation["dng_candidate_reason"] == (
        "RAW file selected for optional DNG interoperability workflow"
    )
    assert operation["observations"] == (
        "DNG candidate: RAW file selected for optional DNG interoperability workflow"
    )


def test_organize_report_identifies_apple_proraw_flow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/IMG_0001.dng"),
            destination=Path("out/2024-08-15_14-32-09.dng"),
            mode="copy",
            raw_format="Apple ProRAW",
            raw_flow="Apple ProRAW / Linear DNG",
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/IMG_0001.dng -> out/2024-08-15_14-32-09.dng",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    operation = report["operations"][0]
    assert operation["raw_family"] is True
    assert operation["raw_format"] == "Apple ProRAW"
    assert operation["raw_flow"] == "Apple ProRAW / Linear DNG"


def test_organize_report_includes_text_normalization_observations(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/Cafe.jpg"),
            destination=Path("out/Café.jpg"),
            mode="copy",
            text_normalization_observations=(
                "filename: normalized Unicode to NFC",
            ),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/Cafe.jpg -> out/Café.jpg",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["operations"][0]["observations"] == (
        "text normalization: filename: normalized Unicode to NFC"
    )


def test_organize_report_includes_date_reconciliation_conflict(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    exif_candidate = MetadataCandidate(
        value=datetime(2020, 1, 2, 3, 4, 5),
        provenance=MetadataProvenance(
            source="EXIF",
            field="DateTimeOriginal",
            confidence="high",
            raw_value="2020:01:02 03:04:05",
        ),
        role="primary",
        precedence=0,
    )
    xmp_candidate = MetadataCandidate(
        value=datetime(2024, 8, 15, 14, 32, 9),
        provenance=MetadataProvenance(
            source="XMP",
            field="xmp:CreateDate",
            confidence="medium",
            raw_value="2024-08-15T14:32:09",
        ),
        role="fallback",
        precedence=2,
    )
    planned = [
        FileOperation(
            source=Path("input/conflict.jpg"),
            destination=Path("out/conflict.jpg"),
            mode="copy",
            date_reconciliation=ReconciliationDecision(
                field="date_taken",
                policy="precedence",
                selected=exif_candidate,
                candidates=(exif_candidate, xmp_candidate),
                reason="selected by metadata precedence policy",
                conflict=True,
            ),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/conflict.jpg -> out/conflict.jpg",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["operations"][0]["observations"] == (
        "date reconciliation: policy=precedence; winner=EXIF:DateTimeOriginal; "
        "reason=selected by metadata precedence policy; "
        "conflicting_sources=EXIF:DateTimeOriginal, XMP:xmp:CreateDate"
    )
    assert report["operations"][0]["conflict"] is True
    assert report["operations"][0]["conflict_sources"] == (
        "EXIF:DateTimeOriginal; XMP:xmp:CreateDate"
    )
    assert report["operations"][0]["conflict_reason"] == (
        "selected by metadata precedence policy"
    )


def test_organize_report_includes_resolved_location(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/good.jpg"),
            destination=Path("out/good.jpg"),
            mode="copy",
            date_provenance=MetadataProvenance(
                source="EXIF",
                field="DateTimeOriginal",
                confidence="high",
                raw_value="2024:08:15 14:32:09",
            ),
            coordinates=GPSCoordinates(
                latitude=-23.5,
                longitude=-46.625,
                provenance=MetadataProvenance(
                    source="EXIF",
                    field="GPSInfo",
                    confidence="high",
                    raw_value={
                        "GPSLatitudeRef": "S",
                        "GPSLatitude": (23, 30, 0),
                        "GPSLongitudeRef": "W",
                        "GPSLongitude": (46, 37, 30),
                    },
                ),
            ),
            location=ReverseGeocodedLocation(
                city="Sao Paulo",
                state="Sao Paulo",
                country="Brazil",
            ),
            location_kind="gps",
            location_status="resolved",
            location_provenance=MetadataProvenance(
                source="Reverse geocoding",
                field="GPSLatitudeDecimal,GPSLongitudeDecimal",
                confidence="medium",
                raw_value={"latitude": -23.5, "longitude": -46.625},
            ),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/good.jpg -> out/good.jpg",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--reverse-geocode",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["location_files"] == 1
    assert report["summary"]["gps_files"] == 1
    assert report["operations"][0]["location_status"] == "resolved"
    assert report["operations"][0]["location_kind"] == "gps"
    assert report["operations"][0]["organization_fallback"] is False
    assert report["operations"][0]["latitude"] == -23.5
    assert report["operations"][0]["longitude"] == -46.625
    assert report["operations"][0]["city"] == "Sao Paulo"
    assert report["operations"][0]["state"] == "Sao Paulo"
    assert report["operations"][0]["country"] == "Brazil"
    assert report["operations"][0]["date_source"] == "EXIF"
    assert report["operations"][0]["date_field"] == "DateTimeOriginal"
    assert report["operations"][0]["date_confidence"] == "high"
    assert report["operations"][0]["chosen_location"] == "Sao Paulo, Sao Paulo, Brazil"
    assert report["operations"][0]["metadata_source"] == "EXIF:DateTimeOriginal"
    assert report["operations"][0]["date_raw_value"] == json.dumps(
        "2024:08:15 14:32:09"
    )
    assert report["operations"][0]["gps_source"] == "EXIF"
    assert report["operations"][0]["gps_field"] == "GPSInfo"
    assert report["operations"][0]["gps_confidence"] == "high"
    assert report["operations"][0]["location_source"] == "Reverse geocoding"
    assert (
        report["operations"][0]["location_field"]
        == "GPSLatitudeDecimal,GPSLongitudeDecimal"
    )
    assert report["operations"][0]["location_confidence"] == "medium"


def test_organize_report_marks_missing_gps_when_reverse_geocoding_requested(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/no-gps.png"),
            destination=Path("out/no-gps.png"),
            mode="copy",
            location_status="missing-gps",
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/no-gps.png -> out/no-gps.png",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--reverse-geocode",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["missing_gps_files"] == 1
    assert report["summary"]["gps_files"] == 0
    assert report["operations"][0]["location_status"] == "missing-gps"
    assert report["operations"][0]["location_kind"] == "none"
    assert report["operations"][0]["organization_fallback"] is False
    assert report["operations"][0]["latitude"] == ""
    assert report["operations"][0]["longitude"] == ""
    assert report["operations"][0]["city"] == ""
    assert report["operations"][0]["state"] == ""
    assert report["operations"][0]["country"] == ""


def test_organize_report_marks_inferred_location_without_gps(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/inferred.jpg"),
            destination=Path("out/inferred.jpg"),
            mode="copy",
            location=ReverseGeocodedLocation(
                city="Paraty",
                state="RJ",
                country="Brasil",
            ),
            location_kind="inferred",
            location_status="inferred",
            location_provenance=MetadataProvenance(
                source="External manifest",
                field="inferred.location.json",
                confidence="low",
                raw_value={"city": "Paraty", "state": "RJ", "country": "Brasil"},
            ),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/inferred.jpg -> out/inferred.jpg",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--reverse-geocode",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["gps_files"] == 0
    assert report["operations"][0]["location_status"] == "inferred"
    assert report["operations"][0]["location_kind"] == "inferred"
    assert report["operations"][0]["latitude"] == ""
    assert report["operations"][0]["longitude"] == ""
    assert report["operations"][0]["location_source"] == "External manifest"


def test_organize_report_marks_correction_manifest_source(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    manifest_path = tmp_path / "corrections.json"
    planned = [
        FileOperation(
            source=Path("input/legacy.jpg"),
            destination=Path("out/legacy.jpg"),
            mode="copy",
            date_provenance=MetadataProvenance(
                source="Correction manifest",
                field="file:legacy.jpg",
                confidence="high",
                raw_value={"date": "1969-07-20T20:17:00"},
            ),
            correction_manifest=CorrectionApplication(
                source_path=manifest_path,
                selectors=("file:legacy.jpg",),
                date_value="1969-07-20T20:17:00",
                event_name="Moon landing",
                priority="highest",
            ),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/legacy.jpg -> out/legacy.jpg",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    operation = report["operations"][0]
    assert operation["date_source"] == "Correction manifest"
    assert operation["event_name"] == "Moon landing"
    assert "correction manifest:" in operation["observations"]
    assert str(manifest_path) in operation["observations"]


def test_organize_report_identifies_derived_asset(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "execution.json"
    planned = [
        FileOperation(
            source=Path("input/IMG_0001_edited.jpg"),
            destination=Path("out/Derivatives/2024/08/15/IMG_0001_edited.jpg"),
            mode="copy",
            asset_role="derived",
            derived=True,
            derived_reason="matched pattern *_edit*",
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/IMG_0001_edited.jpg -> out/Derivatives/2024/08/15/IMG_0001_edited.jpg",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    operation = json.loads(report_path.read_text(encoding="utf-8"))["operations"][0]
    assert operation["asset_role"] == "derived"
    assert operation["derived"] is True
    assert operation["derived_reason"] == "matched pattern *_edit*"
    assert operation["observations"] == "derived asset: matched pattern *_edit*"


def test_import_report_is_final_batch_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "import-manifest.json"
    chosen_date = datetime(2024, 8, 15, 14, 32, 9)
    planned = [
        FileOperation(
            source=Path("camera/IMG_0001.jpg"),
            destination=Path("library/2024/08/15/IMG_0001.jpg"),
            mode="copy",
            chosen_date=chosen_date,
            date_provenance=MetadataProvenance(
                source="EXIF",
                field="DateTimeOriginal",
                confidence="high",
                raw_value="2024:08:15 14:32:09",
            ),
            location=ReverseGeocodedLocation(
                city="Paraty",
                state="RJ",
                country="Brazil",
            ),
            location_provenance=MetadataProvenance(
                source="Reverse geocoding",
                field="GPSLatitudeDecimal,GPSLongitudeDecimal",
                confidence="medium",
                raw_value={"latitude": -23.2, "longitude": -44.7},
            ),
            location_status="resolved",
            location_kind="gps",
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY camera/IMG_0001.jpg -> library/2024/08/15/IMG_0001_01.jpg"
        ],
    )

    result = main([
        "import",
        "./camera",
        "--output",
        "./library",
        "--report",
        str(report_path),
    ])

    assert result == 0
    operation = json.loads(report_path.read_text(encoding="utf-8"))["operations"][0]
    assert operation["source"] == "camera/IMG_0001.jpg"
    assert operation["destination"] == "library/2024/08/15/IMG_0001_01.jpg"
    assert operation["chosen_date"] == "2024-08-15T14:32:09"
    assert operation["chosen_location"] == "Paraty, RJ, Brazil"
    assert operation["metadata_source"] == "EXIF:DateTimeOriginal"
    assert operation["conflict"] is False


def test_organize_writes_valid_csv_execution_report(
    tmp_path: Path, monkeypatch
) -> None:
    report_path = tmp_path / "reports" / "execution.csv"
    planned = [
        FileOperation(
            source=Path("input/good.jpg"),
            destination=Path("out/good.jpg"),
            mode="copy",
            date_fallback=False,
        ),
        FileOperation(
            source=Path("input/bad.jpg"),
            destination=Path("out/bad.jpg"),
            mode="copy",
            date_fallback=False,
        ),
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/good.jpg -> out/good.jpg",
            "[ERROR] COPY input/bad.jpg -> out/bad.jpg (error: permission denied)",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    with report_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.DictReader(report_file))

    assert rows == [
        {
            "source": "input/good.jpg",
            "destination": "out/good.jpg",
            "action": "copy",
            "status": "success",
            "observations": "",
            "date_source": "",
            "date_field": "",
            "date_confidence": "",
            "date_raw_value": "",
            "chosen_date": "",
            "chosen_location": "",
            "metadata_source": "",
            "conflict": "False",
            "conflict_sources": "",
            "conflict_reason": "",
            "date_kind": "captured",
            "event_name": "",
            "sidecar_count": "0",
            "sidecar_sources": "",
            "sidecar_destinations": "",
            "raw_family": "False",
            "raw_format": "",
            "raw_flow": "",
            "asset_role": "original",
            "derived": "False",
            "derived_reason": "",
            "dng_candidate": "False",
            "dng_candidate_reason": "",
        },
        {
            "source": "input/bad.jpg",
            "destination": "out/bad.jpg",
            "action": "copy",
            "status": "error",
            "observations": "permission denied",
            "date_source": "",
            "date_field": "",
            "date_confidence": "",
            "date_raw_value": "",
            "chosen_date": "",
            "chosen_location": "",
            "metadata_source": "",
            "conflict": "False",
            "conflict_sources": "",
            "conflict_reason": "",
            "date_kind": "captured",
            "event_name": "",
            "sidecar_count": "0",
            "sidecar_sources": "",
            "sidecar_destinations": "",
            "raw_family": "False",
            "raw_format": "",
            "raw_flow": "",
            "asset_role": "original",
            "derived": "False",
            "derived_reason": "",
            "dng_candidate": "False",
            "dng_candidate_reason": "",
        },
    ]


# ---------------------------------------------------------------------------
# --clock-offset CLI flag
# ---------------------------------------------------------------------------

def test_organize_accepts_clock_offset_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--clock-offset",
        "+3h",
    ])

    assert result == 0
    assert captured["clock_offset"] == "+3h"


def test_organize_accepts_clock_offset_day_format_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    # Negative offsets must use the = form to avoid argparse treating the
    # leading '-' as an option prefix.
    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--clock-offset=-1d",
    ])

    assert result == 0
    assert captured["clock_offset"] == "-1d"


def test_organize_rejects_invalid_clock_offset(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([
            "organize",
            "./photos",
            "--output",
            "./organized",
            "--clock-offset",
            "bad-offset",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid --clock-offset" in captured.err


def test_organize_accepts_clock_offset_from_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "behavior": {"clock_offset": "+01:00"},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main(["organize", "./photos", "--config", str(config_path)])

    assert result == 0
    assert captured["clock_offset"] == "+01:00"


def test_organize_cli_clock_offset_overrides_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "behavior": {"clock_offset": "+01:00"},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_plan(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", fake_plan)
    monkeypatch.setattr("photo_organizer.cli.apply_operations", lambda *_args, **_kwargs: [])

    result = main([
        "organize",
        "./photos",
        "--config",
        str(config_path),
        "--clock-offset",
        "+3h",
    ])

    assert result == 0
    assert captured["clock_offset"] == "+3h"


def test_organize_report_includes_clock_offset_and_original_datetime(
    tmp_path: Path, monkeypatch
) -> None:
    """Report observations include clock_offset and the original datetime."""
    report_path = tmp_path / "execution.json"
    original_dt = datetime(2020, 6, 15, 10, 0, 0)
    corrected_dt = datetime(2020, 6, 15, 13, 0, 0)

    planned = [
        FileOperation(
            source=Path("input/a.jpg"),
            destination=Path("out/a.jpg"),
            mode="copy",
            date_provenance=MetadataProvenance(
                source="Correction manifest",
                field="global:clock_offset",
                confidence="high",
                raw_value={
                    "manifest": ".",
                    "selectors": ("global:clock_offset",),
                    "timezone": None,
                    "clock_offset": "+3h",
                    "base_source": "EXIF:DateTimeOriginal",
                    "base_value": original_dt.isoformat(),
                },
            ),
            correction_manifest=CorrectionApplication(
                source_path=Path("."),
                selectors=("global:clock_offset",),
                clock_offset="+3h",
                priority="highest",
            ),
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_args, **_kwargs: planned,
    )
    monkeypatch.setattr(
        "photo_organizer.cli.apply_operations",
        lambda *_args, **_kwargs: [
            "[INFO] COPY input/a.jpg -> out/a.jpg",
        ],
    )

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--copy",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    observations = report["operations"][0]["observations"]
    assert "clock_offset=+3h" in observations
    assert f"original_datetime={original_dt.isoformat()}" in observations


# ---------------------------------------------------------------------------
# --staging-dir CLI flag
# ---------------------------------------------------------------------------

def test_organize_accepts_staging_dir_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_apply(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", lambda *_a, **_k: [])
    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--staging-dir",
        "/tmp/staging",
    ])

    assert result == 0
    assert captured.get("staging_dir") == "/tmp/staging"


def test_import_accepts_staging_dir_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_apply(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", lambda *_a, **_k: [])
    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main([
        "import",
        "./photos",
        "--output",
        "./organized",
        "--staging-dir",
        "/tmp/staging",
    ])

    assert result == 0
    assert captured.get("staging_dir") == "/tmp/staging"


def test_organize_staging_dir_from_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "behavior": {"staging_dir": "/tmp/my-staging"},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_apply(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", lambda *_a, **_k: [])
    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main(["organize", "./photos", "--config", str(config_path)])

    assert result == 0
    assert captured.get("staging_dir") == "/tmp/my-staging"


def test_organize_cli_staging_dir_overrides_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "behavior": {"staging_dir": "/tmp/config-staging"},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_apply(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", lambda *_a, **_k: [])
    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main([
        "organize",
        "./photos",
        "--config",
        str(config_path),
        "--staging-dir",
        "/tmp/cli-staging",
    ])

    assert result == 0
    assert captured.get("staging_dir") == "/tmp/cli-staging"


def test_organize_accepts_conflict_policy_from_cli(monkeypatch) -> None:
    captured = {}

    def fake_apply(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", lambda *_a, **_k: [])
    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main([
        "organize",
        "./photos",
        "--output",
        "./organized",
        "--conflict-policy",
        "skip",
    ])

    assert result == 0
    assert captured.get("conflict_policy") == "skip"


def test_organize_conflict_policy_from_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "organized"),
                "behavior": {"conflict_policy": "quarantine"},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_apply(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("photo_organizer.cli.plan_organization_operations", lambda *_a, **_k: [])
    monkeypatch.setattr("photo_organizer.cli.apply_operations", fake_apply)

    result = main(["organize", "./photos", "--config", str(config_path)])

    assert result == 0
    assert captured.get("conflict_policy") == "quarantine"


def test_organize_fail_fast_conflict_policy_returns_error(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    source = source_dir / "IMG_0001.jpg"
    source.write_text("new")
    ts = datetime(2024, 8, 15, 14, 32, 9).timestamp()
    os.utime(source, (ts, ts))
    destination = output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing")

    result = main([
        "organize",
        str(source_dir),
        "--output",
        str(output_dir),
        "--copy",
        "--conflict-policy",
        "fail-fast",
    ])

    assert result == 1
    assert destination.read_text() == "existing"
    assert source.exists()


def test_organize_skip_conflict_policy_reports_skipped_operation(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    output_dir = tmp_path / "organized"
    report_path = tmp_path / "report.json"
    source = source_dir / "IMG_0001.jpg"
    source.write_text("new")
    ts = datetime(2024, 8, 15, 14, 32, 9).timestamp()
    os.utime(source, (ts, ts))
    destination = output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing")

    result = main([
        "organize",
        str(source_dir),
        "--output",
        str(output_dir),
        "--copy",
        "--conflict-policy",
        "skip",
        "--report",
        str(report_path),
    ])

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["processed_files"] == 0
    assert report["operations"][0]["status"] == "skipped"
    assert report["operations"][0]["observations"] == "conflict: destination exists"
    assert destination.read_text() == "existing"
    assert source.exists()


def test_organize_staging_end_to_end_promotes_files(
    tmp_path: Path,
    caplog,
) -> None:
    """End-to-end: files are staged then promoted; staging dir is cleaned up."""
    import os

    source_dir = tmp_path / "photos"
    output_dir = tmp_path / "organized"
    staging_dir = tmp_path / "staging"
    source_dir.mkdir()

    img = source_dir / "IMG_1.jpg"
    img.write_text("image-data")
    ts = datetime(2024, 8, 15, 14, 32, 9).timestamp()
    os.utime(img, (ts, ts))

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            str(source_dir),
            "--output",
            str(output_dir),
            "--copy",
            "--staging-dir",
            str(staging_dir),
        ])

    assert result == 0
    final = output_dir / "2024" / "08" / "15" / "2024-08-15_14-32-09.jpg"
    assert final.exists()
    assert final.read_text() == "image-data"
    # Source must still exist (copy mode).
    assert img.exists()
    # Staging dir must be cleaned up.
    assert not staging_dir.exists()
    assert "Staging enabled" in caplog.text
    assert "promoting" in caplog.text


def test_organize_staging_failure_leaves_output_untouched(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    """When staging fails the output directory is not created."""
    output_dir = tmp_path / "organized"
    staging_dir = tmp_path / "staging"

    planned = [
        FileOperation(
            source=Path("ghost.jpg"),  # does not exist
            destination=output_dir / "2024" / "01" / "01" / "ghost.jpg",
            mode="copy",
        )
    ]

    monkeypatch.setattr(
        "photo_organizer.cli.plan_organization_operations",
        lambda *_a, **_k: planned,
    )

    with caplog.at_level(logging.INFO):
        result = main([
            "organize",
            "./photos",
            "--output",
            str(output_dir),
            "--copy",
            "--staging-dir",
            str(staging_dir),
        ])

    assert result == 0  # command exits 0; errors are in the report
    assert not output_dir.exists()
    assert not staging_dir.exists()
