"""dbt-forge presets — reusable project configuration templates."""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_FIELDS = {
    "adapter",
    "marts",
    "packages",
    "add_examples",
    "add_sqlfluff",
    "ci_providers",
    "add_unit_tests",
    "add_metricflow",
    "add_snapshot",
    "add_seed",
    "add_exposure",
    "add_macro",
    "add_pre_commit",
    "add_env_config",
    "team_owner",
}

VALID_ADAPTERS = {
    "BigQuery",
    "Snowflake",
    "PostgreSQL",
    "DuckDB",
    "Databricks",
    "Redshift",
    "Trino",
    "Spark",
}

VALID_CI_PROVIDERS = {"GitHub Actions", "GitLab CI", "Bitbucket Pipelines"}


@dataclass
class PresetConfig:
    name: str = ""
    description: str = ""
    defaults: dict = field(default_factory=dict)
    locked: list[str] = field(default_factory=list)


def load_preset(path_or_url: str) -> PresetConfig:
    """Load a preset from a local file path or HTTPS URL."""
    if path_or_url.startswith("https://"):
        with urllib.request.urlopen(path_or_url) as response:  # noqa: S310
            content = response.read().decode("utf-8")
    else:
        content = Path(path_or_url).read_text()

    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("Preset file must be a YAML mapping.")

    return PresetConfig(
        name=data.get("name", ""),
        description=data.get("description", ""),
        defaults=data.get("defaults", {}),
        locked=data.get("locked", []),
    )


def validate_preset(preset: PresetConfig) -> list[str]:
    """Validate a preset and return list of error messages (empty = valid)."""
    errors: list[str] = []

    # Check for unknown fields in defaults
    for key in preset.defaults:
        if key not in VALID_FIELDS:
            errors.append(f"Unknown field in defaults: '{key}'")

    # Check for unknown fields in locked
    for key in preset.locked:
        if key not in VALID_FIELDS:
            errors.append(f"Unknown field in locked: '{key}'")

    # Validate locked fields have defaults
    for key in preset.locked:
        if key not in preset.defaults:
            errors.append(f"Locked field '{key}' has no default value")

    # Validate specific field values
    if "adapter" in preset.defaults:
        if preset.defaults["adapter"] not in VALID_ADAPTERS:
            errors.append(
                f"Invalid adapter '{preset.defaults['adapter']}'. "
                f"Must be one of: {', '.join(sorted(VALID_ADAPTERS))}"
            )

    if "ci_providers" in preset.defaults:
        for p in preset.defaults["ci_providers"]:
            if p not in VALID_CI_PROVIDERS:
                errors.append(f"Invalid CI provider '{p}'")

    return errors


def apply_preset_defaults(preset: PresetConfig, current: dict) -> dict:
    """Apply preset defaults to a config dict. Locked fields override; defaults fill gaps."""
    result = dict(current)
    for key, value in preset.defaults.items():
        if key in preset.locked:
            result[key] = value
        elif key not in result or result[key] is None:
            result[key] = value
    return result
