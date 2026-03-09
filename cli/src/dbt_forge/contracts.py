"""dbt-forge contracts — data contract generation logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dbt_forge.introspect.base import WarehouseIntrospector
from dbt_forge.scanner import find_sql_models, parse_yml_models


@dataclass
class ContractColumn:
    name: str
    data_type: str
    is_nullable: bool = True
    existing_description: str = ""
    existing_tests: list[str] = field(default_factory=list)


def introspect_model_columns(
    introspector: WarehouseIntrospector,
    schema: str,
    model: str,
) -> list[ContractColumn]:
    """Get column metadata from warehouse for a model."""
    columns = introspector.get_columns(schema, model)
    return [
        ContractColumn(
            name=col.name,
            data_type=col.data_type,
            is_nullable=col.is_nullable,
        )
        for col in columns
    ]


def generate_contract(
    yml_path: Path,
    model_name: str,
    columns: list[ContractColumn],
) -> str:
    """Generate updated YAML content with contract enforcement."""
    if yml_path.exists():
        data = yaml.safe_load(yml_path.read_text())
    else:
        data = {"version": 2, "models": []}

    if not data:
        data = {"version": 2, "models": []}

    # Find or create model entry
    model_entry = None
    for model in data.get("models", []):
        if isinstance(model, dict) and model.get("name") == model_name:
            model_entry = model
            break

    if model_entry is None:
        model_entry = {"name": model_name, "columns": []}
        data.setdefault("models", []).append(model_entry)

    # Add contract config
    config = model_entry.setdefault("config", {})
    config["contract"] = {"enforced": True}

    # Build existing column map
    existing_cols: dict[str, dict] = {}
    for col in model_entry.get("columns", []):
        if isinstance(col, dict) and "name" in col:
            existing_cols[col["name"]] = col

    # Merge introspected columns with existing
    new_columns = []
    for col in columns:
        existing = existing_cols.get(col.name, {})

        col_entry: dict = {"name": col.name}

        # Preserve existing description
        if existing.get("description"):
            col_entry["description"] = existing["description"]
        elif col.existing_description:
            col_entry["description"] = col.existing_description

        # Add data_type
        col_entry["data_type"] = col.data_type

        # Preserve existing tests and add not_null if needed
        existing_tests = existing.get("tests", existing.get("data_tests", []))
        tests = list(existing_tests) if existing_tests else []

        if not col.is_nullable:
            has_not_null = any(
                (t == "not_null" if isinstance(t, str) else "not_null" in t) for t in tests
            )
            if not has_not_null:
                tests.append("not_null")

        if tests:
            col_entry["data_tests"] = tests

        new_columns.append(col_entry)

    model_entry["columns"] = new_columns

    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def find_public_models(root: Path) -> list[str]:
    """Find models marked as access: public in YAML."""
    public_models = []
    yml_models = parse_yml_models(root)

    for yml_path in set(yml_models.values()):
        try:
            data = yaml.safe_load(yml_path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "models" not in data:
            continue
        for model in data["models"]:
            if not isinstance(model, dict):
                continue
            access = model.get("access", "")
            config = model.get("config", {})
            config_access = config.get("access", "") if isinstance(config, dict) else ""
            if access == "public" or config_access == "public":
                public_models.append(model["name"])

    return public_models


def get_model_schema(root: Path, model_name: str) -> str | None:
    """Infer the schema for a model from dbt_project.yml or path conventions."""
    dbt_project = root / "dbt_project.yml"
    if not dbt_project.exists():
        return None

    try:
        data = yaml.safe_load(dbt_project.read_text())
    except yaml.YAMLError:
        return None

    # Check for custom schema in dbt_project.yml models config
    project_name = data.get("name", "")

    # Try to find the model and infer schema from path
    for sql_path in find_sql_models(root):
        if sql_path.stem == model_name:
            rel = str(sql_path.relative_to(root / "models"))
            parts = rel.split("/")
            if len(parts) > 1:
                # Convention: models/<schema_folder>/... -> schema = project_schema_folder
                return parts[0]

    return project_name or None
