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
