import json
from pathlib import Path

import pytest

from photo_organizer.config import ConfigurationError, load_organization_config


def test_load_organization_config_reads_json_rules(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "output": "organized",
                "naming": {"pattern": "{date:%Y%m%d}_{stem}{ext}"},
                "destination": {
                    "pattern": "{date:%Y}/{date:%m}",
                    "strategy": "date",
                },
                "behavior": {
                    "mode": "copy",
                    "dry_run": True,
                    "plan": False,
                    "reverse_geocode": False,
                    "reconciliation_policy": "newest",
                    "date_heuristics": False,
                    "location_inference": False,
                    "correction_manifest": "corrections.csv",
                    "correction_priority": "metadata",
                },
                "preview": {"heic": True},
                "interop": {"dng_candidates": True},
                "events": {
                    "window_minutes": 45,
                    "directory": True,
                    "directory_pattern": "{date:%Y}/{date:%m}/{date:%Y-%m-%d}_{event}",
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.output == "organized"
    assert config.naming_pattern == "{date:%Y%m%d}_{stem}{ext}"
    assert config.destination_pattern == "{date:%Y}/{date:%m}"
    assert config.organization_strategy == "date"
    assert config.mode == "copy"
    assert config.dry_run is True
    assert config.plan is False
    assert config.reverse_geocode is False
    assert config.reconciliation_policy == "newest"
    assert config.date_heuristics is False
    assert config.location_inference is False
    assert config.correction_manifest == "corrections.csv"
    assert config.correction_priority == "metadata"
    assert config.heic_preview is True
    assert config.dng_candidates is True
    assert config.event_window_minutes == 45
    assert config.event_directory is True
    assert config.event_directory_pattern == (
        "{date:%Y}/{date:%m}/{date:%Y-%m-%d}_{event}"
    )


def test_load_organization_config_reads_yaml_rules(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.yaml"
    config_path.write_text(
        """
output: organized
naming:
  pattern: "{date:%Y%m%d}_{stem}{ext}"
destination:
  pattern: "{date:%Y}/{date:%m}"
behavior:
  mode: copy
""".lstrip(),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.output == "organized"
    assert config.naming_pattern == "{date:%Y%m%d}_{stem}{ext}"
    assert config.destination_pattern == "{date:%Y}/{date:%m}"
    assert config.mode == "copy"


def test_load_organization_config_rejects_invalid_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"mode": "delete"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="behavior.mode"):
        load_organization_config(config_path)


def test_load_organization_config_rejects_invalid_reconciliation_policy(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"reconciliation_policy": "random"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="reconciliation_policy"):
        load_organization_config(config_path)


def test_load_organization_config_rejects_invalid_correction_priority(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"correction_priority": "random"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="correction_priority"):
        load_organization_config(config_path)


def test_load_organization_config_accepts_city_state_month_strategy(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "destination": {"strategy": "city-state-month"},
                "behavior": {"mode": "copy"},
            }
        ),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.organization_strategy == "city-state-month"


def test_load_organization_config_accepts_event_strategy(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"destination": {"strategy": "event"}}),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.organization_strategy == "event"


def test_load_organization_config_rejects_unknown_pattern_field(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"naming": {"pattern": "{unknown}{ext}"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="Invalid naming.pattern"):
        load_organization_config(config_path)


def test_load_organization_config_reads_clock_offset(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"clock_offset": "+3h"}}),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.clock_offset == "+3h"


def test_load_organization_config_rejects_invalid_clock_offset(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"clock_offset": "bad-offset"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="clock_offset"):
        load_organization_config(config_path)


def test_load_organization_config_accepts_day_clock_offset(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"clock_offset": "-1d"}}),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.clock_offset == "-1d"


def test_load_organization_config_rejects_invalid_heic_preview(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"preview": {"heic": "yes"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="preview.heic"):
        load_organization_config(config_path)


def test_load_organization_config_rejects_invalid_dng_candidates(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"interop": {"dng_candidates": "yes"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="interop.dng_candidates"):
        load_organization_config(config_path)


def test_load_organization_config_rejects_invalid_event_window(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"events": {"window_minutes": 0}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="events.window_minutes"):
        load_organization_config(config_path)


def test_load_organization_config_reads_staging_dir(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"staging_dir": "/tmp/staging"}}),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.staging_dir == "/tmp/staging"


def test_load_organization_config_reads_conflict_policy(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"conflict_policy": "overwrite-never"}}),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.conflict_policy == "overwrite-never"


def test_load_organization_config_reads_derivative_rules(tmp_path: Path) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps(
            {
                "derivatives": {
                    "enabled": True,
                    "path": "Working",
                    "patterns": ["*-proof", "*_retouched*"],
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_organization_config(config_path)

    assert config.segregate_derivatives is True
    assert config.derivative_path == "Working"
    assert config.derivative_patterns == ("*-proof", "*_retouched*")


def test_load_organization_config_rejects_absolute_derivative_path(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"derivatives": {"path": "/tmp/Working"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="derivatives.path"):
        load_organization_config(config_path)


def test_load_organization_config_rejects_invalid_conflict_policy(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(
        json.dumps({"behavior": {"conflict_policy": "replace"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="behavior.conflict_policy"):
        load_organization_config(config_path)


def test_load_organization_config_staging_dir_defaults_to_none(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "organizer.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")

    config = load_organization_config(config_path)

    assert config.staging_dir is None
