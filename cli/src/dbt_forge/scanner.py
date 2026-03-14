"""Shared scanner utilities for analyzing dbt project structure."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console

console = Console()


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) to find dbt_project.yml."""
    current = start or Path.cwd()
    for directory in [current, *current.parents]:
        if (directory / "dbt_project.yml").exists():
            return directory
    console.print(
        "[red]Error:[/red] No [bold]dbt_project.yml[/bold] found.\n"
        "Run this command from inside a dbt project."
    )
    raise typer.Exit(1)


def find_sql_models(root: Path) -> list[Path]:
    """Find all SQL model files under models/."""
    models_dir = root / "models"
    if not models_dir.exists():
        return []
    return sorted(models_dir.rglob("*.sql"))


def find_yml_files(root: Path) -> list[Path]:
    """Find all YAML files under models/."""
    models_dir = root / "models"
    if not models_dir.exists():
        return []
    return sorted(list(models_dir.rglob("*.yml")) + list(models_dir.rglob("*.yaml")))


def parse_yml_models(root: Path) -> dict[str, Path]:
    """Parse all model names from YAML files. Returns {model_name: yml_path}."""
    models: dict[str, Path] = {}
    models_dir = root / "models"
    if not models_dir.exists():
        return models
    for path in list(models_dir.rglob("*.yml")) + list(models_dir.rglob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "models" not in data:
            continue
        for model in data["models"]:
            if isinstance(model, dict) and "name" in model:
                models[model["name"]] = path
    return models


def parse_yml_tests(root: Path) -> set[str]:
    """Find all model names that have at least one test defined."""
    import re

    tested: set[str] = set()
    yml_files = list((root / "models").rglob("*.yml")) if (root / "models").exists() else []
    yml_files += list((root / "tests").rglob("*.yml")) if (root / "tests").exists() else []

    for path in yml_files:
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not data:
            continue
        for model in data.get("models", []):
            if not isinstance(model, dict):
                continue
            model_name = model.get("name", "")
            for col in model.get("columns", []):
                if isinstance(col, dict) and (col.get("tests") or col.get("data_tests")):
                    tested.add(model_name)
                    break
        for unit_test in data.get("unit_tests", []):
            if isinstance(unit_test, dict) and "model" in unit_test:
                tested.add(unit_test["model"])

    tests_dir = root / "tests"
    if tests_dir.exists():
        for sql_file in tests_dir.rglob("*.sql"):
            content = sql_file.read_text()
            refs = re.findall(r"ref\(['\"](\w+)['\"]\)", content)
            tested.update(refs)

    return tested


def count_models_by_layer(root: Path) -> dict[str, int]:
    """Categorize SQL models by layer (staging/intermediate/marts/other)."""
    counts: dict[str, int] = {"staging": 0, "intermediate": 0, "marts": 0, "other": 0}
    for model in find_sql_models(root):
        rel = str(model.relative_to(root))
        if "staging" in rel:
            counts["staging"] += 1
        elif "intermediate" in rel:
            counts["intermediate"] += 1
        elif "marts" in rel:
            counts["marts"] += 1
        else:
            counts["other"] += 1
    return counts


def parse_sources(root: Path) -> list[dict]:
    """Extract source definitions from YAML files."""
    sources: list[dict] = []
    for path in find_yml_files(root):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "sources" not in data:
            continue
        for source in data["sources"]:
            if not isinstance(source, dict):
                continue
            has_freshness = "freshness" in source or "freshness" in (source.get("config") or {})
            sources.append(
                {
                    "name": source.get("name", "unknown"),
                    "has_freshness": has_freshness,
                }
            )
    return sources


def parse_packages(root: Path) -> list[dict]:
    """Parse packages.yml entries."""
    packages_path = root / "packages.yml"
    if not packages_path.exists():
        return []
    try:
        data = yaml.safe_load(packages_path.read_text())
    except yaml.YAMLError:
        return []
    if not data or "packages" not in data:
        return []
    result = []
    for pkg in data["packages"]:
        if isinstance(pkg, dict) and "package" in pkg:
            name = pkg["package"].split("/")[-1] if "/" in pkg["package"] else pkg["package"]
            result.append({"name": name, "version": pkg.get("version", "unpinned")})
    return result
