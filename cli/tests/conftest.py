"""Shared fixtures for dbt-forge tests, including E2E integration helpers."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers (not fixtures — importable by test modules)
# ---------------------------------------------------------------------------


def run_dbt(
    project_dir: Path,
    *args: str,
    env_override: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run ``dbt <args>`` as a subprocess inside *project_dir*."""
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(project_dir / "profiles")
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["dbt", *args],
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def run_forge(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run ``dbt-forge <args>`` via the current Python interpreter."""
    return subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Session-scoped E2E project fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_project_dir():
    """Generate a dbt-forge project with DuckDB, seed data, and run dbt deps/seed/run."""
    from dbt_forge.generator.project import generate_project
    from dbt_forge.prompts.questions import ProjectConfig

    with tempfile.TemporaryDirectory() as tmpdir:
        config = ProjectConfig(
            project_name="e2e_project",
            adapter="DuckDB",
            marts=["finance", "marketing"],
            packages=["dbt-utils"],
            add_examples=True,
            add_sqlfluff=False,
            add_seed=True,
            add_unit_tests=True,
            add_macro=True,
            add_snapshot=True,
            add_env_config=False,
            output_dir=tmpdir,
        )
        generate_project(config)

        project_dir = Path(tmpdir) / "e2e_project"

        # Patch source YAML: remove database line (DuckDB doesn't use it)
        sources_yml = project_dir / "models/staging/example_source/_example_source__sources.yml"
        content = sources_yml.read_text()
        lines = [line for line in content.splitlines(keepends=True) if "database:" not in line]
        sources_yml.write_text("".join(lines))

        # Seed DuckDB with raw source data
        import duckdb

        db_path = str(project_dir / "e2e_project_dev.duckdb")
        conn = duckdb.connect(db_path)
        conn.execute("CREATE SCHEMA IF NOT EXISTS raw_example")
        conn.execute("""
            CREATE TABLE raw_example.orders (
                id INTEGER,
                customer_id INTEGER,
                status VARCHAR,
                amount INTEGER,
                created_at TIMESTAMP,
                _loaded_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO raw_example.orders VALUES
            (1, 100, 'completed', 5000, '2024-01-15', CURRENT_TIMESTAMP, '2024-01-15'),
            (2, 101, 'shipped',   3000, '2024-01-16', CURRENT_TIMESTAMP, '2024-01-16'),
            (3, 102, 'placed',    1500, '2024-01-17', CURRENT_TIMESTAMP, '2024-01-17'),
            (4, 100, 'cancelled',  800, '2024-01-18', CURRENT_TIMESTAMP, '2024-01-18'),
            (5, 103, 'completed', 9200, '2024-01-19', CURRENT_TIMESTAMP, '2024-01-19')
        """)
        conn.close()

        # Run dbt deps to install packages
        result = run_dbt(project_dir, "deps")
        assert result.returncode == 0, f"dbt deps failed:\n{result.stdout}\n{result.stderr}"

        # Run dbt seed + run to materialize all models (needed for tests)
        result = run_dbt(project_dir, "seed")
        assert result.returncode == 0, f"dbt seed failed:\n{result.stdout}\n{result.stderr}"

        result = run_dbt(project_dir, "run")
        assert result.returncode == 0, f"dbt run failed:\n{result.stdout}\n{result.stderr}"

        yield project_dir
