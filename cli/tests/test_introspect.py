"""Tests for warehouse introspection."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from dbt_forge.introspect.base import ColumnMetadata, TableMetadata, WarehouseIntrospector
from dbt_forge.introspect.connectors import ADAPTER_MAP, _quote_identifier, get_introspector
from dbt_forge.introspect.profile_reader import read_profile, resolve_env_vars


class MockIntrospector(WarehouseIntrospector):
    """Mock introspector for testing."""

    def __init__(self, schemas=None, tables=None, columns=None, **kwargs):
        self._schemas = schemas or ["public"]
        self._tables = tables or {}
        self._columns = columns or {}

    def connect(self):
        pass

    def close(self):
        pass

    def list_schemas(self):
        return self._schemas

    def list_tables(self, schema):
        return self._tables.get(schema, [])

    def get_columns(self, schema, table):
        return self._columns.get(f"{schema}.{table}", [])


class TestColumnMetadata:
    def test_defaults(self):
        col = ColumnMetadata(name="id", data_type="INTEGER")
        assert col.is_nullable is True
        assert col.comment == ""


class TestTableMetadata:
    def test_defaults(self):
        t = TableMetadata(schema_name="public", table_name="users", table_type="TABLE")
        assert t.columns == []
        assert t.row_count is None


class TestMockIntrospector:
    def test_context_manager(self):
        m = MockIntrospector()
        with m as inst:
            assert inst.list_schemas() == ["public"]

    def test_list_tables(self):
        tables = [TableMetadata(schema_name="public", table_name="users", table_type="TABLE")]
        m = MockIntrospector(tables={"public": tables})
        assert m.list_tables("public") == tables

    def test_get_columns(self):
        cols = [ColumnMetadata(name="id", data_type="INTEGER")]
        m = MockIntrospector(columns={"public.users": cols})
        assert m.get_columns("public", "users") == cols


class TestGetIntrospector:
    def test_unsupported_adapter(self):
        with pytest.raises(ValueError, match="Unsupported adapter"):
            get_introspector("oracle")

    def test_supported_adapters(self):
        for adapter_key in ADAPTER_MAP:
            assert adapter_key in ADAPTER_MAP


class TestQuoteIdentifier:
    def test_allows_hyphens_and_leading_digits(self):
        assert _quote_identifier("sales-raw") == '"sales-raw"'
        assert _quote_identifier("2024_schema") == '"2024_schema"'

    def test_quotes_each_dotted_part(self):
        assert _quote_identifier("analytics.sales-raw") == '"analytics"."sales-raw"'
        assert _quote_identifier("main.orders", quote_char="`") == "`main`.`orders`"

    def test_rejects_control_characters(self):
        with pytest.raises(ValueError, match="Invalid schema"):
            _quote_identifier("bad\nschema", label="schema")

    def test_rejects_empty_identifier_parts(self):
        with pytest.raises(ValueError, match="Invalid schema"):
            _quote_identifier("analytics..orders", label="schema")


class TestResolveEnvVars:
    def test_simple_env_var(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "hello")
        assert resolve_env_vars("{{ env_var('MY_VAR') }}") == "hello"

    def test_env_var_with_default(self):
        result = resolve_env_vars("{{ env_var('NONEXISTENT_VAR_XYZ', 'fallback') }}")
        assert result == "fallback"

    def test_no_env_var(self):
        assert resolve_env_vars("plain text") == "plain text"

    def test_multiple_env_vars(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "5432")
        result = resolve_env_vars("{{ env_var('HOST') }}:{{ env_var('PORT') }}")
        assert result == "localhost:5432"


class TestReadProfile:
    def test_reads_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "profiles.yml").write_text(
                "my_project:\n"
                "  target: dev\n"
                "  outputs:\n"
                "    dev:\n"
                "      type: duckdb\n"
                "      path: dev.duckdb\n"
            )
            adapter_type, config = read_profile(Path(tmpdir), target=None)
            assert adapter_type == "duckdb"
            assert config["path"] == "dev.duckdb"

    def test_specific_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "profiles.yml").write_text(
                "my_project:\n"
                "  target: dev\n"
                "  outputs:\n"
                "    dev:\n"
                "      type: duckdb\n"
                "      path: dev.duckdb\n"
                "    prod:\n"
                "      type: snowflake\n"
                "      account: myaccount\n"
            )
            adapter_type, config = read_profile(Path(tmpdir), target="prod")
            assert adapter_type == "snowflake"

    def test_missing_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "profiles.yml").write_text(
                "my_project:\n"
                "  target: dev\n"
                "  outputs:\n"
                "    dev:\n"
                "      type: duckdb\n"
                "      path: dev.duckdb\n"
            )
            with pytest.raises(ValueError, match="not found"):
                read_profile(Path(tmpdir), target="staging")

    def test_no_profiles_yml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                read_profile(Path(tmpdir))

    def test_env_var_resolution(self, monkeypatch):
        monkeypatch.setenv("DB_PATH", "/data/warehouse.duckdb")
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "profiles.yml").write_text(
                "my_project:\n"
                "  target: dev\n"
                "  outputs:\n"
                "    dev:\n"
                "      type: duckdb\n"
                "      path: \"{{ env_var('DB_PATH') }}\"\n"
            )
            adapter_type, config = read_profile(Path(tmpdir))
            assert config["path"] == "/data/warehouse.duckdb"


class TestIntrospectedTemplates:
    """Test that the introspected source templates render correctly."""

    def test_source_yml_template(self):
        from dbt_forge.generator.renderer import render_template

        cols = [
            ColumnMetadata(name="id", data_type="INTEGER", is_nullable=False),
            ColumnMetadata(name="name", data_type="VARCHAR", is_nullable=True),
        ]
        tables = [
            TableMetadata(schema_name="raw", table_name="users", table_type="TABLE", columns=cols),
        ]
        result = render_template(
            "add/introspected_sources.yml.j2",
            {
                "source_name": "raw_data",
                "schema": "raw",
                "tables": tables,
            },
        )
        assert "name: raw_data" in result
        assert "schema: raw" in result
        assert "name: users" in result
        assert "name: id" in result
        assert "data_type: INTEGER" in result
        assert "not_null" in result  # id is not nullable

    def test_stg_model_template(self):
        from dbt_forge.generator.renderer import render_template

        cols = [
            ColumnMetadata(name="id", data_type="INTEGER"),
            ColumnMetadata(name="name", data_type="VARCHAR"),
        ]
        result = render_template(
            "add/introspected_stg_model.sql.j2",
            {
                "source_name": "raw_data",
                "table_name": "users",
                "columns": cols,
            },
        )
        assert "source('raw_data', 'users')" in result
        assert "id," in result
        assert "name" in result
        assert "select * from renamed" in result


class TestDuckDBIntrospector:
    """Integration tests using a real in-memory DuckDB."""

    def test_list_schemas(self):
        from dbt_forge.introspect.connectors import DuckDBIntrospector

        with DuckDBIntrospector(path=":memory:") as intro:
            schemas = intro.list_schemas()
            assert "main" in schemas

    def test_list_tables(self):
        from dbt_forge.introspect.connectors import DuckDBIntrospector

        intro = DuckDBIntrospector(path=":memory:")
        intro.connect()
        intro._conn.execute("CREATE TABLE main.users (id INTEGER, name VARCHAR)")
        tables = intro.list_tables("main")
        names = [t.table_name for t in tables]
        assert "users" in names
        intro.close()

    def test_get_columns(self):
        from dbt_forge.introspect.connectors import DuckDBIntrospector

        intro = DuckDBIntrospector(path=":memory:")
        intro.connect()
        intro._conn.execute(
            "CREATE TABLE main.orders (id INTEGER NOT NULL, amount DOUBLE, status VARCHAR)"
        )
        cols = intro.get_columns("main", "orders")
        assert len(cols) == 3
        col_map = {c.name: c for c in cols}
        assert col_map["id"].data_type == "INTEGER"
        assert col_map["id"].is_nullable is False
        assert col_map["amount"].is_nullable is True
        assert col_map["status"].data_type == "VARCHAR"
        intro.close()

    def test_list_tables_with_views(self):
        from dbt_forge.introspect.connectors import DuckDBIntrospector

        intro = DuckDBIntrospector(path=":memory:")
        intro.connect()
        intro._conn.execute("CREATE TABLE main.raw_data (id INTEGER)")
        intro._conn.execute("CREATE VIEW main.v_data AS SELECT * FROM main.raw_data")
        tables = intro.list_tables("main")
        names = [t.table_name for t in tables]
        assert "raw_data" in names
        assert "v_data" in names
        intro.close()

    def test_empty_schema(self):
        from dbt_forge.introspect.connectors import DuckDBIntrospector

        with DuckDBIntrospector(path=":memory:") as intro:
            tables = intro.list_tables("main")
            assert tables == []

    def test_full_introspect_flow(self):
        """End-to-end: create tables, introspect, verify metadata."""
        from dbt_forge.introspect.connectors import DuckDBIntrospector

        with DuckDBIntrospector(path=":memory:") as intro:
            intro._conn.execute(
                "CREATE TABLE main.customers "
                "(customer_id INTEGER NOT NULL, email VARCHAR, created_at TIMESTAMP)"
            )
            intro._conn.execute(
                "CREATE TABLE main.orders "
                "(order_id INTEGER NOT NULL, customer_id INTEGER, total DECIMAL(10,2))"
            )

            schemas = intro.list_schemas()
            assert "main" in schemas

            tables = intro.list_tables("main")
            assert len(tables) == 2

            customer_cols = intro.get_columns("main", "customers")
            assert len(customer_cols) == 3
            assert customer_cols[0].name == "customer_id"
            assert customer_cols[0].is_nullable is False

            order_cols = intro.get_columns("main", "orders")
            assert len(order_cols) == 3
            assert order_cols[2].name == "total"
