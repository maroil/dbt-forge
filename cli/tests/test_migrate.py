"""Tests for the migrate CLI command."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dbt_forge.cli.migrate import run_migrate


class TestRunMigrate:
    """End-to-end tests for the migrate command."""

    def test_basic_migration(self, tmp_path: Path) -> None:
        """Create SQL files with cross-references and verify migration output."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        # Source-reading model
        (sql_dir / "create_stg_orders.sql").write_text(
            "CREATE TABLE staging.orders AS SELECT * FROM raw.orders"
        )
        # Model that depends on staging
        (sql_dir / "create_order_summary.sql").write_text(
            "CREATE VIEW marts.order_summary AS SELECT count(*) FROM staging.orders"
        )

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        # Verify staging model was created
        staging_files = list((out_dir / "models" / "staging").rglob("*.sql"))
        assert len(staging_files) >= 1

        # Verify marts model was created
        marts_files = list((out_dir / "models" / "marts").rglob("*.sql"))
        assert len(marts_files) >= 1

        # Verify source YAML was created
        source_ymls = list((out_dir / "models" / "staging").rglob("*sources.yml"))
        assert len(source_ymls) >= 1

        # Check source YAML content
        source_content = source_ymls[0].read_text()
        assert "raw" in source_content
        assert "orders" in source_content

        # Verify migration report
        report = out_dir / "migration_report.md"
        assert report.exists()
        report_content = report.read_text()
        assert "Migration Report" in report_content
        assert "2" in report_content  # 2 SQL files scanned

    def test_ref_substitution(self, tmp_path: Path) -> None:
        """Verify that raw table references are replaced with ref()/source()."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "stg.sql").write_text("CREATE TABLE stg_users AS SELECT * FROM raw.users")
        (sql_dir / "mart.sql").write_text("CREATE TABLE dim_users AS SELECT * FROM stg_users")

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        # Find the marts model SQL
        mart_files = list((out_dir / "models" / "marts").rglob("*.sql"))
        assert len(mart_files) >= 1
        mart_sql = mart_files[0].read_text()
        assert "ref(" in mart_sql

    def test_dry_run_no_files(self, tmp_path: Path) -> None:
        """Dry run should not write any files."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "test.sql").write_text("CREATE TABLE orders AS SELECT * FROM raw.orders")

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir), dry_run=True)

        # No models directory should be created
        assert not (out_dir / "models").exists()
        assert not (out_dir / "migration_report.md").exists()

    def test_no_sql_files(self, tmp_path: Path) -> None:
        """Empty directory should produce no output."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()

        run_migrate(sql_dir=str(sql_dir), output_dir=str(tmp_path))

        assert not (tmp_path / "models").exists()

    def test_invalid_directory(self, tmp_path: Path) -> None:
        """Non-existent directory should print error."""
        run_migrate(sql_dir=str(tmp_path / "nonexistent"), output_dir=str(tmp_path))
        # Should not crash

    def test_model_yaml_generated(self, tmp_path: Path) -> None:
        """Verify model YAML files are generated."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "orders.sql").write_text(
            "CREATE TABLE staging.orders AS SELECT * FROM raw.orders"
        )

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        yml_files = list(out_dir.rglob("*__models.yml"))
        assert len(yml_files) >= 1
        yml_content = yml_files[0].read_text()
        assert "version: 2" in yml_content
        assert "Migrated from" in yml_content

    def test_three_layer_pipeline(self, tmp_path: Path) -> None:
        """Test staging -> intermediate -> marts pipeline detection."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "01_stg.sql").write_text("CREATE TABLE stg_events AS SELECT * FROM raw.events")
        (sql_dir / "02_int.sql").write_text(
            "CREATE TABLE int_events AS SELECT * FROM stg_events WHERE active = true"
        )
        (sql_dir / "03_mart.sql").write_text("CREATE TABLE dim_events AS SELECT * FROM int_events")

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        # Check that all three layers have models
        report = (out_dir / "migration_report.md").read_text()
        assert "staging" in report
        assert "intermediate" in report
        assert "marts" in report

    def test_source_with_schema(self, tmp_path: Path) -> None:
        """Source detection should use schema name."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "model.sql").write_text(
            dedent("""\
            CREATE TABLE analytics.user_agg AS
            SELECT * FROM warehouse.users
            JOIN warehouse.orders ON users.id = orders.user_id
        """)
        )

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        source_ymls = list((out_dir / "models" / "staging").rglob("*sources.yml"))
        assert len(source_ymls) >= 1
        content = source_ymls[0].read_text()
        assert "warehouse" in content

    def test_strip_create_prefix(self, tmp_path: Path) -> None:
        """Generated SQL should not contain CREATE TABLE prefix."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "model.sql").write_text(
            "CREATE TABLE my_table AS SELECT id, name FROM raw.source_table"
        )

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        sql_files = list(out_dir.rglob("*.sql"))
        assert len(sql_files) >= 1
        for sf in sql_files:
            content = sf.read_text()
            assert "CREATE TABLE" not in content.upper()

    def test_source_substitution_in_staging(self, tmp_path: Path) -> None:
        """Staging models should use source() not ref()."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "stg.sql").write_text("CREATE TABLE stg_users AS SELECT * FROM raw_db.users")

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        sql_files = list(out_dir.rglob("*.sql"))
        assert sql_files
        content = sql_files[0].read_text()
        assert "source(" in content

    def test_cte_handling(self, tmp_path: Path) -> None:
        """CTEs should not be treated as external table references."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "model.sql").write_text(
            "CREATE TABLE result AS\n"
            "WITH base AS (\n"
            "  SELECT * FROM raw.events\n"
            ")\n"
            "SELECT * FROM base"
        )

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        # "base" should NOT appear as a source
        source_ymls = list(out_dir.rglob("*sources.yml"))
        for yml in source_ymls:
            content = yml.read_text()
            assert "base" not in content

    def test_migration_report_counts(self, tmp_path: Path) -> None:
        """Migration report should have correct counts."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        (sql_dir / "a.sql").write_text("CREATE TABLE a AS SELECT * FROM ext.t1")
        (sql_dir / "b.sql").write_text("CREATE TABLE b AS SELECT * FROM a")
        (sql_dir / "c.sql").write_text("CREATE TABLE c AS SELECT * FROM b")

        run_migrate(sql_dir=str(sql_dir), output_dir=str(out_dir))

        report = (out_dir / "migration_report.md").read_text()
        assert "3" in report  # 3 files scanned or 3 models
