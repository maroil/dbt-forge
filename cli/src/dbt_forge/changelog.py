"""dbt-forge changelog — model change detection between git refs."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


@dataclass
class ModelChange:
    model_name: str
    change_type: str  # added, removed, modified, column_added, column_removed, type_changed
    details: str
    is_breaking: bool
    commit_hash: str = ""
    commit_date: str = ""


def _git_run(root: Path, *args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _get_latest_tag(root: Path) -> str | None:
    """Get the most recent git tag."""
    tag = _git_run(root, "describe", "--tags", "--abbrev=0")
    return tag if tag else None


def _get_file_at_ref(root: Path, ref: str, path: str) -> str | None:
    """Get file content at a specific git ref."""
    content = _git_run(root, "show", f"{ref}:{path}")
    return content if content else None


def _get_changed_files(root: Path, from_ref: str, to_ref: str) -> list[dict]:
    """Get files changed between two refs with their status."""
    output = _git_run(root, "diff", "--name-status", f"{from_ref}...{to_ref}", "--", "models/")
    if not output:
        return []

    files = []
    for line in output.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            status, filepath = parts
            files.append({"status": status[0], "path": filepath})
    return files


def _get_commit_info(root: Path, from_ref: str, to_ref: str, path: str) -> tuple[str, str]:
    """Get latest commit hash and date for a file change."""
    log = _git_run(root, "log", "--format=%H %aI", "-1", f"{from_ref}...{to_ref}", "--", path)
    if log:
        parts = log.split(" ", 1)
        if len(parts) == 2:
            return parts[0][:8], parts[1]
    return "", ""


def _parse_yml_columns(yml_content: str, model_name: str) -> dict[str, str]:
    """Extract column name -> data_type from YAML for a model."""
    try:
        data = yaml.safe_load(yml_content)
    except yaml.YAMLError:
        return {}
    if not data:
        return {}

    columns: dict[str, str] = {}
    for model in data.get("models", []):
        if not isinstance(model, dict) or model.get("name") != model_name:
            continue
        for col in model.get("columns", []):
            if isinstance(col, dict) and "name" in col:
                columns[col["name"]] = col.get("data_type", "")
    return columns


def _detect_column_changes(
    model_name: str,
    old_cols: dict[str, str],
    new_cols: dict[str, str],
    commit_hash: str,
    commit_date: str,
) -> list[ModelChange]:
    """Detect column additions, removals, and type changes."""
    changes: list[ModelChange] = []

    removed = set(old_cols) - set(new_cols)
    added = set(new_cols) - set(old_cols)
    common = set(old_cols) & set(new_cols)

    for col in sorted(removed):
        changes.append(
            ModelChange(
                model_name=model_name,
                change_type="column_removed",
                details=f"Column '{col}' removed",
                is_breaking=True,
                commit_hash=commit_hash,
                commit_date=commit_date,
            )
        )

    for col in sorted(added):
        changes.append(
            ModelChange(
                model_name=model_name,
                change_type="column_added",
                details=f"Column '{col}' added",
                is_breaking=False,
                commit_hash=commit_hash,
                commit_date=commit_date,
            )
        )

    for col in sorted(common):
        old_type = old_cols[col]
        new_type = new_cols[col]
        if old_type and new_type and old_type != new_type:
            changes.append(
                ModelChange(
                    model_name=model_name,
                    change_type="type_changed",
                    details=f"Column '{col}' type: {old_type} -> {new_type}",
                    is_breaking=True,
                    commit_hash=commit_hash,
                    commit_date=commit_date,
                )
            )

    return changes


def detect_changes_between_refs(
    repo_root: Path, from_ref: str, to_ref: str = "HEAD"
) -> list[ModelChange]:
    """Detect all model changes between two git refs."""
    changes: list[ModelChange] = []
    changed_files = _get_changed_files(repo_root, from_ref, to_ref)

    for file_info in changed_files:
        status = file_info["status"]
        filepath = file_info["path"]
        commit_hash, commit_date = _get_commit_info(repo_root, from_ref, to_ref, filepath)

        if filepath.endswith(".sql"):
            model_name = Path(filepath).stem
            if status == "A":
                changes.append(
                    ModelChange(
                        model_name=model_name,
                        change_type="added",
                        details=f"New model: {filepath}",
                        is_breaking=False,
                        commit_hash=commit_hash,
                        commit_date=commit_date,
                    )
                )
            elif status == "D":
                changes.append(
                    ModelChange(
                        model_name=model_name,
                        change_type="removed",
                        details=f"Deleted model: {filepath}",
                        is_breaking=True,
                        commit_hash=commit_hash,
                        commit_date=commit_date,
                    )
                )
            elif status == "M":
                changes.append(
                    ModelChange(
                        model_name=model_name,
                        change_type="modified",
                        details=f"Modified: {filepath}",
                        is_breaking=False,
                        commit_hash=commit_hash,
                        commit_date=commit_date,
                    )
                )

        elif filepath.endswith((".yml", ".yaml")):
            # Detect column-level changes from YAML diffs
            old_content = _get_file_at_ref(repo_root, from_ref, filepath)
            new_content = _get_file_at_ref(repo_root, to_ref, filepath)

            if old_content and new_content:
                try:
                    old_data = yaml.safe_load(old_content) or {}
                    new_data = yaml.safe_load(new_content) or {}
                except yaml.YAMLError:
                    continue

                old_models = {
                    m["name"]: m
                    for m in old_data.get("models", [])
                    if isinstance(m, dict) and "name" in m
                }
                new_models = {
                    m["name"]: m
                    for m in new_data.get("models", [])
                    if isinstance(m, dict) and "name" in m
                }

                for model_name in set(old_models) | set(new_models):
                    old_cols = {}
                    new_cols = {}
                    if model_name in old_models:
                        for col in old_models[model_name].get("columns", []):
                            if isinstance(col, dict) and "name" in col:
                                old_cols[col["name"]] = col.get("data_type", "")
                    if model_name in new_models:
                        for col in new_models[model_name].get("columns", []):
                            if isinstance(col, dict) and "name" in col:
                                new_cols[col["name"]] = col.get("data_type", "")

                    col_changes = _detect_column_changes(
                        model_name, old_cols, new_cols, commit_hash, commit_date
                    )
                    changes.extend(col_changes)

    return changes


def render_changelog_markdown(changes: list[ModelChange]) -> str:
    """Render changes as markdown."""
    if not changes:
        return "No model changes detected.\n"

    breaking = [c for c in changes if c.is_breaking]
    non_breaking = [c for c in changes if not c.is_breaking]

    lines = ["# Changelog", ""]

    if breaking:
        lines.append("## Breaking Changes")
        lines.append("")
        for c in breaking:
            prefix = f"`{c.commit_hash}`" if c.commit_hash else ""
            lines.append(f"- **{c.model_name}**: {c.details} {prefix}")
        lines.append("")

    if non_breaking:
        lines.append("## Changes")
        lines.append("")
        for c in non_breaking:
            prefix = f"`{c.commit_hash}`" if c.commit_hash else ""
            lines.append(f"- **{c.model_name}**: {c.details} {prefix}")
        lines.append("")

    return "\n".join(lines)


def render_changelog_json(changes: list[ModelChange]) -> str:
    """Render changes as JSON."""
    return json.dumps([asdict(c) for c in changes], indent=2)
