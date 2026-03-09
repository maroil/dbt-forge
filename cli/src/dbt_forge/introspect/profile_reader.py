"""Read and parse dbt profiles.yml to extract connection configuration."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml


def resolve_env_vars(value: str) -> str:
    """Resolve {{ env_var('X') }} and {{ env_var('X', 'default') }} patterns."""

    def _replace(match):
        args = match.group(1).split(",")
        var_name = args[0].strip().strip("'\"")
        default = args[1].strip().strip("'\"") if len(args) > 1 else None
        return os.environ.get(var_name, default or "")

    return re.sub(r"\{\{\s*env_var\(([^)]+)\)\s*\}\}", _replace, value)


def _resolve_dict(d: dict) -> dict:
    """Recursively resolve env vars in dict values."""
    result = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k] = resolve_env_vars(v)
        elif isinstance(v, dict):
            result[k] = _resolve_dict(v)
        else:
            result[k] = v
    return result


def read_profile(project_root: Path, target: str | None = None) -> tuple[str, dict]:
    """Read profiles.yml and return (adapter_type, connection_config).

    Looks for profiles.yml in project_root/profiles/ first, then ~/.dbt/.
    """
    candidates = [
        project_root / "profiles" / "profiles.yml",
        Path.home() / ".dbt" / "profiles.yml",
    ]

    profiles_path = None
    for c in candidates:
        if c.exists():
            profiles_path = c
            break

    if profiles_path is None:
        raise FileNotFoundError("No profiles.yml found")

    raw = profiles_path.read_text()
    data = yaml.safe_load(raw)
    if not data:
        raise ValueError("Empty profiles.yml")

    # Get first profile
    for _profile_name, profile in data.items():
        if not isinstance(profile, dict) or "outputs" not in profile:
            continue
        target_name = target or profile.get("target", "dev")
        outputs = profile["outputs"]
        if target_name not in outputs:
            available = ", ".join(outputs.keys())
            raise ValueError(f"Target '{target_name}' not found. Available: {available}")
        target_config = _resolve_dict(outputs[target_name])
        adapter_type = target_config.pop("type", "unknown")
        return adapter_type, target_config

    raise ValueError("No valid profile found in profiles.yml")
