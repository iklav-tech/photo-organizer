"""Batch correction manifest loading and matching."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import fnmatch
import json
from pathlib import Path
from typing import Any, Literal


CorrectionPriority = Literal["highest", "metadata", "heuristic"]
CORRECTION_PRIORITY_CHOICES = ("highest", "metadata", "heuristic")


@dataclass(frozen=True)
class CorrectionRule:
    selector: str
    selector_type: str
    camera_make: str | None = None
    camera_model: str | None = None
    date_value: str | None = None
    timezone: str | None = None
    clock_offset: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    event_name: str | None = None
    priority: CorrectionPriority | None = None


@dataclass(frozen=True)
class CorrectionApplication:
    source_path: Path
    selectors: tuple[str, ...]
    date_value: str | None = None
    timezone: str | None = None
    clock_offset: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    event_name: str | None = None
    priority: CorrectionPriority = "highest"

    @property
    def location(self) -> dict[str, str | None] | None:
        if self.city is None and self.state is None and self.country is None:
            return None
        return {
            "city": self.city,
            "state": self.state,
            "country": self.country,
        }


@dataclass(frozen=True)
class CorrectionManifest:
    path: Path
    rules: tuple[CorrectionRule, ...]
    priority: CorrectionPriority = "highest"


class CorrectionManifestError(ValueError):
    """Raised when a correction manifest cannot be loaded or validated."""


def validate_correction_priority(priority: str) -> CorrectionPriority:
    if priority not in CORRECTION_PRIORITY_CHOICES:
        allowed = ", ".join(CORRECTION_PRIORITY_CHOICES)
        raise ValueError(f"Unknown correction priority '{priority}'. Allowed: {allowed}")
    return priority  # type: ignore[return-value]


def _load_raw_manifest(path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise CorrectionManifestError("YAML correction manifests require PyYAML") from exc
        with path.open(encoding="utf-8") as manifest_file:
            return yaml.safe_load(manifest_file)
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as manifest_file:
            return list(csv.DictReader(manifest_file))
    raise CorrectionManifestError(
        "Correction manifest must end with .json, .yaml, .yml or .csv"
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _rule_from_mapping(
    mapping: dict[str, Any],
    default_priority: CorrectionPriority,
) -> CorrectionRule:
    selector_type = _string_or_none(mapping.get("selector_type"))
    selector = None
    for candidate_type in (
        "file",
        "path",
        "folder",
        "glob",
        "pattern",
        "camera",
        "camera_profile",
        "camera_model",
    ):
        value = _string_or_none(mapping.get(candidate_type))
        if value is not None:
            selector_type = selector_type or candidate_type
            selector = value
            break
    if selector is None:
        selector = _string_or_none(mapping.get("selector"))
    if selector_type is None:
        selector_type = "glob"
    camera_make = _string_or_none(mapping.get("camera_make") or mapping.get("make"))
    camera_model = _string_or_none(mapping.get("camera_model") or mapping.get("model"))
    if selector is None and (camera_make is not None or camera_model is not None):
        selector_type = "camera"
        selector = " ".join(
            part for part in (camera_make, camera_model) if part is not None
        )
    if selector is None:
        raise CorrectionManifestError(
            "Correction rule requires file, folder, glob, camera or selector"
        )

    priority = _string_or_none(mapping.get("priority"))
    return CorrectionRule(
        selector=selector,
        selector_type=selector_type,
        camera_make=camera_make,
        camera_model=camera_model,
        date_value=_string_or_none(
            mapping.get("date")
            or mapping.get("datetime")
            or mapping.get("date_taken")
        ),
        timezone=_string_or_none(mapping.get("timezone") or mapping.get("tz")),
        clock_offset=_string_or_none(
            mapping.get("clock_offset")
            or mapping.get("camera_clock_offset")
            or mapping.get("offset")
        ),
        city=_string_or_none(mapping.get("city")),
        state=_string_or_none(mapping.get("state")),
        country=_string_or_none(mapping.get("country")),
        event_name=_string_or_none(mapping.get("event") or mapping.get("event_name")),
        priority=validate_correction_priority(priority) if priority else default_priority,
    )


def load_correction_manifest(path: str | Path) -> CorrectionManifest:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise CorrectionManifestError(f"Correction manifest does not exist: {manifest_path}")
    if not manifest_path.is_file():
        raise CorrectionManifestError(f"Correction manifest path is not a file: {manifest_path}")

    raw_manifest = _load_raw_manifest(manifest_path)
    default_priority = "highest"
    raw_rules = raw_manifest
    if isinstance(raw_manifest, dict):
        priority = _string_or_none(raw_manifest.get("priority"))
        if priority is not None:
            default_priority = validate_correction_priority(priority)
        raw_rules = raw_manifest.get("rules", [])
    if not isinstance(raw_rules, list):
        raise CorrectionManifestError("Correction manifest rules must be a list")

    rules = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            raise CorrectionManifestError("Correction manifest rule must be an object")
        rules.append(_rule_from_mapping(raw_rule, default_priority))

    return CorrectionManifest(
        path=manifest_path,
        rules=tuple(rules),
        priority=default_priority,
    )


def _relative_path(path: Path, source_root: Path | None) -> str:
    if source_root is None:
        return path.name
    try:
        return path.relative_to(source_root).as_posix()
    except ValueError:
        return path.name


def _matches_rule(rule: CorrectionRule, file_path: Path, source_root: Path | None) -> bool:
    return _matches_rule_with_profile(rule, file_path, source_root, None)


def _normalize_camera_text(value: str | None) -> str:
    return " ".join(str(value or "").casefold().split())


def _matches_camera_value(expected: str | None, actual: str | None) -> bool:
    if expected is None:
        return True
    expected_text = _normalize_camera_text(expected)
    actual_text = _normalize_camera_text(actual)
    return bool(actual_text) and fnmatch.fnmatch(actual_text, expected_text)


def _matches_camera_rule(
    rule: CorrectionRule,
    camera_profile: dict[str, str] | None,
) -> bool:
    if camera_profile is None:
        return False

    make = camera_profile.get("make")
    model = camera_profile.get("model")
    profile = camera_profile.get("profile") or " ".join(
        part for part in (make, model) if part
    )

    if rule.selector_type == "camera_model":
        selector_match = _matches_camera_value(rule.selector, model)
    else:
        selector_match = _matches_camera_value(rule.selector, profile) or (
            rule.selector_type in {"camera", "camera_profile"}
            and (
                _matches_camera_value(rule.selector, model)
                or _matches_camera_value(rule.selector, make)
            )
        )

    return (
        selector_match
        and _matches_camera_value(rule.camera_make, make)
        and _matches_camera_value(rule.camera_model, model)
    )


def _matches_rule_with_profile(
    rule: CorrectionRule,
    file_path: Path,
    source_root: Path | None,
    camera_profile: dict[str, str] | None,
) -> bool:
    rel_path = _relative_path(file_path, source_root)
    selector = rule.selector
    selector_type = rule.selector_type

    if selector_type in {"camera", "camera_profile", "camera_model"}:
        return _matches_camera_rule(rule, camera_profile)
    if selector_type in {"file", "path"}:
        return selector in {rel_path, file_path.name, str(file_path)}
    if selector_type == "folder":
        folder = selector.strip("/\\")
        return any(
            parent.name == folder for parent in file_path.parents
        ) or rel_path.startswith(f"{folder}/")
    if selector_type in {"glob", "pattern"}:
        return fnmatch.fnmatch(rel_path, selector) or fnmatch.fnmatch(file_path.name, selector)
    return False


def correction_for_file(
    manifest: CorrectionManifest | None,
    file_path: str | Path,
    source_root: str | Path | None = None,
    priority_override: CorrectionPriority | None = None,
    camera_profile: dict[str, str] | None = None,
) -> CorrectionApplication | None:
    if manifest is None:
        return None

    path = Path(file_path)
    root = Path(source_root) if source_root is not None else None
    matches = [
        rule
        for rule in manifest.rules
        if _matches_rule_with_profile(rule, path, root, camera_profile)
    ]
    if not matches:
        return None

    values: dict[str, str | None] = {
        "date_value": None,
        "timezone": None,
        "clock_offset": None,
        "city": None,
        "state": None,
        "country": None,
        "event_name": None,
    }
    for rule in matches:
        for field_name in values:
            value = getattr(rule, field_name)
            if value is not None:
                values[field_name] = value

    return CorrectionApplication(
        source_path=manifest.path,
        selectors=tuple(f"{rule.selector_type}:{rule.selector}" for rule in matches),
        priority=priority_override or matches[-1].priority or manifest.priority,
        **values,
    )
