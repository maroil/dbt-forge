"""Lint configuration loader for dbt-forge lint."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LintConfig:
    fan_out_threshold: int = 5
    max_cte_count: int = 8
    max_join_count: int = 6
    max_line_count: int = 300
    disabled_rules: list[str] = field(default_factory=list)


def load_lint_config(config_path: Path | None = None, root: Path | None = None) -> LintConfig:
    """Load lint config from file or use defaults."""
    if config_path and config_path.exists():
        return _parse_config(config_path)

    if root:
        default_path = root / ".dbt-forge-lint.yml"
        if default_path.exists():
            return _parse_config(default_path)

    return LintConfig()


def _parse_config(path: Path) -> LintConfig:
    """Parse a YAML lint config file."""
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError:
        return LintConfig()

    if not isinstance(data, dict):
        return LintConfig()

    return LintConfig(
        fan_out_threshold=data.get("fan_out_threshold", 5),
        max_cte_count=data.get("max_cte_count", 8),
        max_join_count=data.get("max_join_count", 6),
        max_line_count=data.get("max_line_count", 300),
        disabled_rules=data.get("disabled_rules", []),
    )
