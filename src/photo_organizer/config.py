"""External configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from photo_organizer.naming import validate_filename_pattern
from photo_organizer.planner import validate_destination_pattern
from photo_organizer.metadata import validate_reconciliation_policy


class ConfigurationError(ValueError):
    """Raised when a user-supplied configuration file is invalid."""


@dataclass(frozen=True)
class OrganizationConfig:
    """Optional organization settings loaded from JSON or YAML."""

    output: str | None = None
    naming_pattern: str | None = None
    destination_pattern: str | None = None
    mode: str | None = None
    dry_run: bool | None = None
    plan: bool | None = None
    reverse_geocode: bool | None = None
    organization_strategy: str | None = None
    reconciliation_policy: str | None = None
    date_heuristics: bool | None = None
    location_inference: bool | None = None


def _load_yaml(path: Path) -> Any:
    try:
        import yaml
    except ImportError:
        try:
            return _load_simple_yaml(path)
        except ConfigurationError:
            raise
        except Exception as fallback_exc:
            raise ConfigurationError(
                "YAML configuration requires PyYAML for this file"
            ) from fallback_exc

    with path.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def _parse_simple_yaml_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return {}
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if text.lower() == "null":
        return None
    if (
        len(text) >= 2
        and text[0] == text[-1]
        and text[0] in {'"', "'"}
    ):
        if text[0] == '"':
            return json.loads(text)
        return text[1:-1]
    return text


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the simple nested mapping format documented for config files."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ConfigurationError(
                f"Invalid YAML indentation at line {line_number}"
            )
        key, separator, value = raw_line.strip().partition(":")
        if not separator or not key:
            raise ConfigurationError(f"Invalid YAML mapping at line {line_number}")

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ConfigurationError(f"Invalid YAML nesting at line {line_number}")

        parent = stack[-1][1]
        parsed_value = _parse_simple_yaml_scalar(value)
        parent[key] = parsed_value
        if isinstance(parsed_value, dict):
            stack.append((indent, parsed_value))
    return root


def _load_raw_config(path: Path) -> Any:
    if not path.exists():
        raise ConfigurationError(f"Configuration file does not exist: {path}")
    if not path.is_file():
        raise ConfigurationError(f"Configuration path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Invalid JSON configuration: {exc}") from exc
    if suffix in {".yaml", ".yml"}:
        return _load_yaml(path)

    raise ConfigurationError("Configuration file must end with .json, .yaml or .yml")


def _expect_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{label} must be an object")
    return value


def _optional_string(section: dict[str, Any], key: str, label: str) -> str | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{label} must be a non-empty string")
    return value


def _optional_bool(section: dict[str, Any], key: str, label: str) -> bool | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ConfigurationError(f"{label} must be a boolean")
    return value


def load_organization_config(config_path: str | Path) -> OrganizationConfig:
    """Load and validate external organize configuration."""
    path = Path(config_path)
    raw_config = _load_raw_config(path)
    if raw_config is None:
        raw_config = {}
    config = _expect_mapping(raw_config, "configuration")

    output = _optional_string(config, "output", "output")

    naming = _expect_mapping(config.get("naming", {}), "naming")
    naming_pattern = _optional_string(naming, "pattern", "naming.pattern")

    destination = _expect_mapping(config.get("destination", {}), "destination")
    destination_pattern = _optional_string(
        destination,
        "pattern",
        "destination.pattern",
    )
    organization_strategy = _optional_string(
        destination,
        "strategy",
        "destination.strategy",
    )

    behavior = _expect_mapping(config.get("behavior", {}), "behavior")
    mode = _optional_string(behavior, "mode", "behavior.mode")
    dry_run = _optional_bool(behavior, "dry_run", "behavior.dry_run")
    plan = _optional_bool(behavior, "plan", "behavior.plan")
    reverse_geocode = _optional_bool(
        behavior,
        "reverse_geocode",
        "behavior.reverse_geocode",
    )
    behavior_strategy = _optional_string(
        behavior,
        "organization_strategy",
        "behavior.organization_strategy",
    )
    reconciliation_policy = _optional_string(
        behavior,
        "reconciliation_policy",
        "behavior.reconciliation_policy",
    )
    date_heuristics = _optional_bool(
        behavior,
        "date_heuristics",
        "behavior.date_heuristics",
    )
    location_inference = _optional_bool(
        behavior,
        "location_inference",
        "behavior.location_inference",
    )

    if organization_strategy is not None and behavior_strategy is not None:
        raise ConfigurationError(
            "Use only one of destination.strategy or behavior.organization_strategy"
        )
    organization_strategy = organization_strategy or behavior_strategy

    if mode is not None and mode not in {"copy", "move"}:
        raise ConfigurationError("behavior.mode must be 'copy' or 'move'")
    if organization_strategy is not None and organization_strategy not in {
        "city-state-month",
        "date",
        "location",
        "location-date",
    }:
        raise ConfigurationError(
            "organization strategy must be 'date', 'location', 'location-date' "
            "or 'city-state-month'"
        )
    if reconciliation_policy is not None:
        try:
            validate_reconciliation_policy(reconciliation_policy)
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid behavior.reconciliation_policy: {exc}"
            ) from exc
    if naming_pattern is not None:
        try:
            validate_filename_pattern(naming_pattern)
        except ValueError as exc:
            raise ConfigurationError(f"Invalid naming.pattern: {exc}") from exc
    if destination_pattern is not None:
        try:
            validate_destination_pattern(destination_pattern)
        except ValueError as exc:
            raise ConfigurationError(f"Invalid destination.pattern: {exc}") from exc

    return OrganizationConfig(
        output=output,
        naming_pattern=naming_pattern,
        destination_pattern=destination_pattern,
        mode=mode,
        dry_run=dry_run,
        plan=plan,
        reverse_geocode=reverse_geocode,
        organization_strategy=organization_strategy,
        reconciliation_policy=reconciliation_policy,
        date_heuristics=date_heuristics,
        location_inference=location_inference,
    )
