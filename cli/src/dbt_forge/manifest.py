"""dbt-forge manifest — tracks generated files for update lifecycle."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from dbt_forge.prompts.questions import ProjectConfig

MANIFEST_FILE = ".dbt-forge.yml"


@dataclass
class ForgeManifest:
    dbt_forge_version: str = ""
    created_at: str = ""
    config: dict = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def config_to_dict(config: ProjectConfig) -> dict:
    """Serialize ProjectConfig to a plain dict."""
    return {
        "project_name": config.project_name,
        "adapter": config.adapter,
        "marts": list(config.marts),
        "packages": list(config.packages),
        "add_examples": config.add_examples,
        "add_sqlfluff": config.add_sqlfluff,
        "ci_providers": list(config.ci_providers),
        "add_unit_tests": config.add_unit_tests,
        "add_metricflow": config.add_metricflow,
        "add_snapshot": config.add_snapshot,
        "add_seed": config.add_seed,
        "add_exposure": config.add_exposure,
        "add_macro": config.add_macro,
        "add_pre_commit": config.add_pre_commit,
        "add_env_config": config.add_env_config,
        "team_owner": config.team_owner,
    }


def dict_to_config(d: dict) -> ProjectConfig:
    """Deserialize a dict back to ProjectConfig."""
    return ProjectConfig(
        project_name=d.get("project_name", "unknown"),
        adapter=d.get("adapter", "BigQuery"),
        marts=d.get("marts", []),
        packages=d.get("packages", []),
        add_examples=d.get("add_examples", True),
        add_sqlfluff=d.get("add_sqlfluff", True),
        ci_providers=d.get("ci_providers", []),
        add_unit_tests=d.get("add_unit_tests", False),
        add_metricflow=d.get("add_metricflow", False),
        add_snapshot=d.get("add_snapshot", False),
        add_seed=d.get("add_seed", False),
        add_exposure=d.get("add_exposure", False),
        add_macro=d.get("add_macro", False),
        add_pre_commit=d.get("add_pre_commit", False),
        add_env_config=d.get("add_env_config", False),
        team_owner=d.get("team_owner", ""),
    )


def write_manifest(base: Path, config: ProjectConfig, generated_files: list[Path]) -> None:
    """Write .dbt-forge.yml manifest after project generation."""
    from dbt_forge import __version__

    files_map: dict[str, str] = {}
    for f in generated_files:
        if f.exists():
            try:
                rel = str(f.relative_to(base))
                files_map[rel] = _hash_content(f.read_text())
            except (ValueError, OSError):
                continue

    manifest = {
        "dbt_forge_version": __version__,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": config_to_dict(config),
        "files": files_map,
    }

    (base / MANIFEST_FILE).write_text(
        yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    )


def read_manifest(base: Path) -> ForgeManifest | None:
    """Read .dbt-forge.yml manifest. Returns None if not found."""
    manifest_path = base / MANIFEST_FILE
    if not manifest_path.exists():
        return None
    try:
        data = yaml.safe_load(manifest_path.read_text())
    except yaml.YAMLError:
        return None
    if not data:
        return None
    return ForgeManifest(
        dbt_forge_version=data.get("dbt_forge_version", ""),
        created_at=data.get("created_at", ""),
        config=data.get("config", {}),
        files=data.get("files", {}),
    )
