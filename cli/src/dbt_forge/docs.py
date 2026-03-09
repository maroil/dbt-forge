"""Documentation utilities -- read/write model schema YAML."""
from __future__ import annotations

from pathlib import Path

import yaml


def find_models_needing_docs(project_root: Path) -> list[dict]:
    """Find models with missing descriptions in their YAML files.

    Returns list of dicts with keys: model_name, yml_path, sql_path, columns,
    existing_descriptions.
    """
    models_dir = project_root / "models"
    if not models_dir.exists():
        return []

    results = []
    for yml_path in sorted(
        list(models_dir.rglob("*.yml")) + list(models_dir.rglob("*.yaml"))
    ):
        try:
            data = yaml.safe_load(yml_path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "models" not in data:
            continue

        for model in data["models"]:
            if not isinstance(model, dict) or "name" not in model:
                continue

            model_name = model["name"]
            model_desc = model.get("description", "")
            columns = model.get("columns", [])

            # Check if any descriptions are missing
            col_names = []
            existing = {}
            has_missing = not model_desc

            for col in columns:
                if isinstance(col, dict) and "name" in col:
                    col_name = col["name"]
                    col_names.append(col_name)
                    col_desc = col.get("description", "")
                    if col_desc:
                        existing[col_name] = col_desc
                    else:
                        has_missing = True

            if not has_missing:
                continue

            # Find corresponding SQL file
            sql_path = _find_sql_for_model(models_dir, model_name)

            results.append({
                "model_name": model_name,
                "yml_path": yml_path,
                "sql_path": sql_path,
                "columns": col_names,
                "existing_descriptions": existing,
                "model_description": model_desc,
            })

    return results


def _find_sql_for_model(models_dir: Path, model_name: str) -> Path | None:
    """Find the SQL file for a given model name."""
    for sql_path in models_dir.rglob(f"{model_name}.sql"):
        return sql_path
    return None


def read_model_sql(sql_path: Path | None) -> str:
    """Read model SQL, returning empty string if not found."""
    if sql_path and sql_path.exists():
        return sql_path.read_text()
    return ""


def update_model_descriptions(
    yml_path: Path,
    model_name: str,
    model_description: str,
    column_descriptions: dict[str, str],
) -> None:
    """Update descriptions in a YAML file, preserving structure."""
    data = yaml.safe_load(yml_path.read_text())
    if not data or "models" not in data:
        return

    for model in data["models"]:
        if not isinstance(model, dict) or model.get("name") != model_name:
            continue

        # Update model description only if empty
        if not model.get("description") and model_description:
            model["description"] = model_description

        # Update column descriptions only if empty
        for col in model.get("columns", []):
            if not isinstance(col, dict) or "name" not in col:
                continue
            col_name = col["name"]
            if not col.get("description") and col_name in column_descriptions:
                col["description"] = column_descriptions[col_name]

        break

    yml_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
