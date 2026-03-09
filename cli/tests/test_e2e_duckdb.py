"""End-to-end integration tests: scaffold a dbt project with DuckDB."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.conftest import run_dbt, run_forge

pytestmark = pytest.mark.integration


def _assert_ok(result, label="command"):
    """Assert subprocess exited 0, with readable error on failure."""
    assert result.returncode == 0, f"{label} failed:\n{result.stdout}\n{result.stderr}"


# ── 3A: Init & Build ────────────────────────────────────────────────


class TestInitAndBuild:
    """Verify the generated project works with real dbt commands."""

    def test_dbt_debug(self, e2e_project_dir: Path):
        result = run_dbt(e2e_project_dir, "debug")
        _assert_ok(result, "dbt debug")
        assert "All checks passed" in result.stdout

    def test_dbt_seed(self, e2e_project_dir: Path):
        """Re-run to verify idempotency (seed ran in fixture)."""
        _assert_ok(run_dbt(e2e_project_dir, "seed"), "dbt seed")

    def test_dbt_run(self, e2e_project_dir: Path):
        """Re-run to verify idempotency (run ran in fixture)."""
        result = run_dbt(e2e_project_dir, "run")
        _assert_ok(result, "dbt run")
        # Intermediates are ephemeral — only staging + mart models appear
        for model in [
            "stg_example_source__orders",
            "finance_orders",
            "marketing_orders",
        ]:
            assert model in result.stdout, f"Model {model} not in dbt run output"

    def test_dbt_test(self, e2e_project_dir: Path):
        _assert_ok(run_dbt(e2e_project_dir, "test"), "dbt test")

    def test_generated_tables_have_correct_data(self, e2e_project_dir: Path):
        import gc

        import duckdb

        db_path = str(e2e_project_dir / "e2e_project_dev.duckdb")
        conn = duckdb.connect(db_path, read_only=True)
        try:
            rows = conn.execute(
                "SELECT * FROM main_finance.finance_orders ORDER BY order_id"
            ).fetchall()
            columns = [desc[0] for desc in conn.description]
        finally:
            conn.close()
            del conn
            gc.collect()

        assert len(rows) == 5
        assert "order_id" in columns
        assert "customer_id" in columns
        assert "status" in columns
        assert "amount_usd" in columns

        first = dict(zip(columns, rows[0]))
        assert first["order_id"] == 1
        assert first["customer_id"] == 100
        assert first["status"] == "completed"
        assert first["amount_usd"] == pytest.approx(50.0)

    def test_dbt_snapshot(self, e2e_project_dir: Path):
        _assert_ok(run_dbt(e2e_project_dir, "snapshot"), "dbt snapshot")


# ── 3B: Add Commands ────────────────────────────────────────────────


class TestAddCommands:
    """Extend the project with add commands, verify artifacts work."""

    def test_add_mart_and_run(self, e2e_project_dir: Path):
        result = run_forge("add", "mart", "analytics", cwd=e2e_project_dir)
        _assert_ok(result, "add mart")

        mart = e2e_project_dir / "models/marts/analytics"
        assert (mart / "analytics_orders.sql").exists()
        inter = "models/intermediate/analytics"
        assert (e2e_project_dir / inter / "int_analytics__orders_enriched.sql").exists()

        result = run_dbt(
            e2e_project_dir,
            "run",
            "--select",
            "+analytics_orders",
        )
        _assert_ok(result, "dbt run analytics")

    def test_add_seed_and_run(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge("add", "seed", "countries", cwd=e2e_project_dir),
            "add seed",
        )
        assert (e2e_project_dir / "seeds/countries.csv").exists()

        result = run_dbt(e2e_project_dir, "seed", "--select", "countries")
        _assert_ok(result, "dbt seed countries")

    def test_add_source_compiles(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge("add", "source", "payments", cwd=e2e_project_dir),
            "add source",
        )
        stg = "models/staging/payments/stg_payments__records.sql"
        assert (e2e_project_dir / stg).exists()

        # compile validates SQL/YAML without needing a real table
        result = run_dbt(
            e2e_project_dir,
            "compile",
            "--select",
            "stg_payments__records",
        )
        _assert_ok(result, "dbt compile payments")

    def test_add_macro_compiles(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge("add", "macro", "safe_divide", cwd=e2e_project_dir),
            "add macro",
        )
        assert (e2e_project_dir / "macros/safe_divide.sql").exists()
        _assert_ok(run_dbt(e2e_project_dir, "compile"), "dbt compile")

    def test_add_exposure_creates_file(self, e2e_project_dir: Path):
        # Use a model name that actually exists in the project
        _assert_ok(
            run_forge(
                "add",
                "exposure",
                "finance_orders",
                cwd=e2e_project_dir,
            ),
            "add exposure",
        )
        path = e2e_project_dir / "models/marts/__finance_orders__exposures.yml"
        assert path.exists()

        content = yaml.safe_load(path.read_text())
        assert "exposures" in content

    def test_add_package_and_install(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge(
                "add",
                "package",
                "dbt-audit-helper",
                cwd=e2e_project_dir,
            ),
            "add package",
        )
        packages = (e2e_project_dir / "packages.yml").read_text()
        assert "audit_helper" in packages

        _assert_ok(run_dbt(e2e_project_dir, "deps"), "dbt deps")

    def test_add_snapshot_compiles(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge("add", "snapshot", "orders_snap", cwd=e2e_project_dir),
            "add snapshot",
        )
        assert (e2e_project_dir / "snapshots/orders_snap.sql").exists()

    def test_add_pre_commit_files(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge("add", "pre-commit", cwd=e2e_project_dir),
            "add pre-commit",
        )
        assert (e2e_project_dir / ".pre-commit-config.yaml").exists()
        assert (e2e_project_dir / ".editorconfig").exists()

    def test_add_ci_files(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge("add", "ci", "github", cwd=e2e_project_dir),
            "add ci",
        )
        assert (e2e_project_dir / ".github/workflows/dbt_ci.yml").exists()

    def test_full_compile_after_all_additions(self, e2e_project_dir: Path):
        # Remove snapshot stub (references a source that doesn't exist)
        snap = e2e_project_dir / "snapshots/orders_snap.sql"
        snap.unlink(missing_ok=True)

        run_dbt(e2e_project_dir, "deps")
        _assert_ok(
            run_dbt(e2e_project_dir, "compile"),
            "dbt compile after all additions",
        )


# ── 3C: Doctor ───────────────────────────────────────────────────────


class TestDoctor:
    """Health checks on the real generated project."""

    def test_doctor_passes_on_clean_project(self, e2e_project_dir: Path):
        _assert_ok(run_forge("doctor", cwd=e2e_project_dir), "doctor")

    def test_doctor_catches_naming_violation(self, e2e_project_dir: Path):
        bad = e2e_project_dir / "models/staging/example_source/BAD_NAME.sql"
        bad.write_text("SELECT 1")
        try:
            result = run_forge(
                "doctor",
                "--check",
                "naming-conventions",
                cwd=e2e_project_dir,
            )
            failed = result.returncode != 0 or "fail" in result.stdout.lower()
            assert failed, "doctor should catch naming violation"
        finally:
            bad.unlink(missing_ok=True)

    def test_doctor_catches_missing_schema(self, e2e_project_dir: Path):
        undoc = e2e_project_dir / "models/marts/finance/undocumented.sql"
        undoc.write_text("SELECT 1 AS id")
        try:
            result = run_forge(
                "doctor",
                "--check",
                "schema-coverage",
                cwd=e2e_project_dir,
            )
            failed = result.returncode != 0 or "fail" in result.stdout.lower()
            assert failed, "doctor should catch missing schema"
        finally:
            undoc.unlink(missing_ok=True)

    def test_doctor_fix_generates_stub(self, e2e_project_dir: Path):
        undoc = e2e_project_dir / "models/marts/finance/undocumented_fix.sql"
        undoc.write_text("SELECT 1 AS id")
        try:
            _assert_ok(
                run_forge("doctor", "--fix", cwd=e2e_project_dir),
                "doctor --fix",
            )
        finally:
            undoc.unlink(missing_ok=True)
            parent = e2e_project_dir / "models/marts/finance"
            for p in parent.glob("*undocumented_fix*"):
                p.unlink(missing_ok=True)

    def test_doctor_ci_exit_code(self, e2e_project_dir: Path):
        bad = e2e_project_dir / "models/staging/example_source/BAD_CI.sql"
        bad.write_text("SELECT 1")
        try:
            result = run_forge("doctor", "--ci", cwd=e2e_project_dir)
            assert result.returncode == 1
        finally:
            bad.unlink(missing_ok=True)


# ── 3D: Status ───────────────────────────────────────────────────────


class TestStatus:
    """Dashboard output."""

    def test_status_shows_model_counts(self, e2e_project_dir: Path):
        result = run_forge("status", cwd=e2e_project_dir)
        _assert_ok(result, "status")
        output = result.stdout.lower()
        assert "staging" in output
        assert "marts" in output


# ── 3E: Update ───────────────────────────────────────────────────────


class TestUpdate:
    """Lifecycle management."""

    def test_update_dry_run_no_changes(self, e2e_project_dir: Path):
        _assert_ok(
            run_forge("update", "--dry-run", cwd=e2e_project_dir),
            "update --dry-run",
        )

    def test_update_detects_modification(self, e2e_project_dir: Path):
        readme = e2e_project_dir / "README.md"
        original = readme.read_text()
        try:
            readme.write_text(original + "\n<!-- modified -->\n")
            result = run_forge("update", "--dry-run", cwd=e2e_project_dir)
            assert result.returncode == 0
            out = result.stdout
            assert "changed" in out.lower() or "README" in out
        finally:
            readme.write_text(original)


# ── 3F: Adapter Profiles ────────────────────────────────────────────


@pytest.mark.parametrize(
    "adapter",
    [
        "BigQuery",
        "Snowflake",
        "PostgreSQL",
        "DuckDB",
        "Databricks",
        "Redshift",
        "Trino",
        "Spark",
    ],
)
def test_adapter_generates_valid_yaml(adapter: str, tmp_path: Path):
    """Each adapter generates parseable dbt_project.yml and profiles."""
    from dbt_forge.generator.project import generate_project
    from dbt_forge.prompts.questions import ProjectConfig

    config = ProjectConfig(
        project_name="adapter_test",
        adapter=adapter,
        marts=["finance"],
        packages=[],
        add_examples=False,
        add_sqlfluff=False,
        output_dir=str(tmp_path),
    )
    generate_project(config)

    project_dir = tmp_path / "adapter_test"

    dbt_project = yaml.safe_load(
        (project_dir / "dbt_project.yml").read_text(),
    )
    assert dbt_project["name"] == "adapter_test"

    profiles = yaml.safe_load(
        (project_dir / "profiles/profiles.yml").read_text(),
    )
    assert "adapter_test" in profiles
    dev_output = profiles["adapter_test"]["outputs"]["dev"]
    expected = adapter.lower().replace(" ", "_").replace("/", "_")
    if expected == "postgresql":
        expected = "postgres"
    assert dev_output["type"] == expected
