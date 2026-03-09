"""Unit tests for the sql_parser module."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dbt_forge.sql_parser import (
    DependencyGraph,
    build_dependency_graph,
    detect_layer,
    extract_table_references,
    parse_create_statement,
    parse_sql_file,
    replace_refs_in_sql,
    topological_sort,
)

# ---------------------------------------------------------------------------
# parse_create_statement
# ---------------------------------------------------------------------------

class TestParseCreateStatement:
    def test_simple_create_table(self) -> None:
        sql = "CREATE TABLE orders AS SELECT * FROM raw.orders"
        result = parse_create_statement(sql)
        assert len(result) == 1
        assert result[0].table_ref.table == "orders"
        assert result[0].table_ref.schema is None
        assert result[0].view_or_table == "TABLE"

    def test_create_view(self) -> None:
        sql = "CREATE VIEW reporting.monthly_sales AS SELECT * FROM sales"
        result = parse_create_statement(sql)
        assert len(result) == 1
        assert result[0].table_ref.table == "monthly_sales"
        assert result[0].table_ref.schema == "reporting"
        assert result[0].view_or_table == "VIEW"

    def test_create_or_replace(self) -> None:
        sql = "CREATE OR REPLACE TABLE analytics.users AS SELECT * FROM raw.users"
        result = parse_create_statement(sql)
        assert len(result) == 1
        assert result[0].table_ref.table == "users"
        assert result[0].table_ref.schema == "analytics"

    def test_create_if_not_exists(self) -> None:
        sql = "CREATE TABLE IF NOT EXISTS staging.events AS SELECT * FROM raw.events"
        result = parse_create_statement(sql)
        assert len(result) == 1
        assert result[0].table_ref.table == "events"
        assert result[0].table_ref.schema == "staging"

    def test_create_temp_table(self) -> None:
        sql = "CREATE TEMPORARY TABLE tmp_data AS SELECT 1"
        result = parse_create_statement(sql)
        assert len(result) == 1
        assert result[0].table_ref.table == "tmp_data"

    def test_create_with_columns(self) -> None:
        sql = "CREATE TABLE users (id INTEGER, name VARCHAR(255), email TEXT)"
        result = parse_create_statement(sql)
        assert len(result) == 1
        assert len(result[0].columns) == 3
        assert result[0].columns[0].name == "id"
        assert result[0].columns[0].data_type == "INTEGER"
        assert result[0].columns[1].name == "name"
        assert result[0].columns[1].data_type == "VARCHAR(255)"

    def test_no_create(self) -> None:
        sql = "SELECT * FROM orders"
        result = parse_create_statement(sql)
        assert len(result) == 0

    def test_multiple_creates(self) -> None:
        sql = dedent("""\
            CREATE TABLE staging.orders AS SELECT * FROM raw.orders;
            CREATE VIEW marts.order_summary AS SELECT * FROM staging.orders;
        """)
        result = parse_create_statement(sql)
        assert len(result) == 2
        assert result[0].table_ref.table == "orders"
        assert result[1].table_ref.table == "order_summary"


# ---------------------------------------------------------------------------
# extract_table_references
# ---------------------------------------------------------------------------

class TestExtractTableReferences:
    def test_simple_from(self) -> None:
        sql = "SELECT * FROM orders"
        refs = extract_table_references(sql)
        assert len(refs) == 1
        assert refs[0].table == "orders"

    def test_schema_qualified(self) -> None:
        sql = "SELECT * FROM raw.orders"
        refs = extract_table_references(sql)
        assert len(refs) == 1
        assert refs[0].schema == "raw"
        assert refs[0].table == "orders"

    def test_join(self) -> None:
        sql = "SELECT * FROM orders JOIN customers ON orders.id = customers.order_id"
        refs = extract_table_references(sql)
        assert len(refs) == 2
        tables = {r.table for r in refs}
        assert "orders" in tables
        assert "customers" in tables

    def test_multiple_joins(self) -> None:
        sql = dedent("""\
            SELECT *
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            LEFT JOIN products p ON o.product_id = p.id
        """)
        refs = extract_table_references(sql)
        tables = {r.table for r in refs}
        assert tables == {"orders", "customers", "products"}

    def test_cte_excluded(self) -> None:
        sql = dedent("""\
            WITH recent_orders AS (
                SELECT * FROM orders WHERE date > '2024-01-01'
            )
            SELECT * FROM recent_orders
        """)
        refs = extract_table_references(sql)
        # recent_orders is a CTE and should be excluded
        tables = {r.table for r in refs}
        assert "orders" in tables
        assert "recent_orders" not in tables

    def test_multiple_ctes_excluded(self) -> None:
        sql = dedent("""\
            WITH cte_a AS (
                SELECT * FROM raw.orders
            ),
            cte_b AS (
                SELECT * FROM cte_a JOIN raw.customers ON 1=1
            )
            SELECT * FROM cte_b
        """)
        refs = extract_table_references(sql)
        tables = {r.table for r in refs}
        assert "raw" not in tables or "orders" in tables
        assert "cte_a" not in tables
        assert "cte_b" not in tables

    def test_deduplication(self) -> None:
        sql = "SELECT * FROM orders UNION ALL SELECT * FROM orders"
        refs = extract_table_references(sql)
        assert len(refs) == 1

    def test_subquery_skipped(self) -> None:
        sql = "SELECT * FROM orders WHERE id IN (SELECT order_id FROM returns)"
        refs = extract_table_references(sql)
        tables = {r.table for r in refs}
        assert "orders" in tables
        assert "returns" in tables


# ---------------------------------------------------------------------------
# parse_sql_file
# ---------------------------------------------------------------------------

class TestParseSqlFile:
    def test_parse_file(self, tmp_path: Path) -> None:
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE staging.orders AS SELECT * FROM raw.orders")
        result = parse_sql_file(sql_file)
        assert result.file_path == sql_file
        assert len(result.creates) == 1
        assert len(result.references) >= 1


# ---------------------------------------------------------------------------
# build_dependency_graph
# ---------------------------------------------------------------------------

class TestBuildDependencyGraph:
    def test_basic_graph(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.sql"
        f1.write_text("CREATE TABLE staging.orders AS SELECT * FROM raw.orders")
        f2 = tmp_path / "b.sql"
        f2.write_text("CREATE VIEW marts.order_summary AS SELECT * FROM staging.orders")

        pf1 = parse_sql_file(f1)
        pf2 = parse_sql_file(f2)
        graph = build_dependency_graph([pf1, pf2])

        assert "staging.orders" in graph.nodes
        assert "marts.order_summary" in graph.nodes
        # order_summary depends on orders
        assert "staging.orders" in graph.edges.get("marts.order_summary", set())

    def test_no_self_reference(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.sql"
        f1.write_text("CREATE TABLE orders AS SELECT * FROM orders WHERE 1=0")
        pf1 = parse_sql_file(f1)
        graph = build_dependency_graph([pf1])
        assert "orders" not in graph.edges.get("orders", set())


# ---------------------------------------------------------------------------
# topological_sort
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_linear_chain(self) -> None:
        graph = DependencyGraph(
            nodes={"a": None, "b": None, "c": None},  # type: ignore[arg-type]
            edges={"a": set(), "b": {"a"}, "c": {"b"}},
        )
        result = topological_sort(graph)
        assert result.index("a") < result.index("b")
        assert result.index("b") < result.index("c")

    def test_independent_nodes(self) -> None:
        graph = DependencyGraph(
            nodes={"a": None, "b": None, "c": None},  # type: ignore[arg-type]
            edges={"a": set(), "b": set(), "c": set()},
        )
        result = topological_sort(graph)
        assert set(result) == {"a", "b", "c"}

    def test_cycle_handled(self) -> None:
        graph = DependencyGraph(
            nodes={"a": None, "b": None},  # type: ignore[arg-type]
            edges={"a": {"b"}, "b": {"a"}},
        )
        result = topological_sort(graph)
        # Both nodes should be in result despite cycle
        assert set(result) == {"a", "b"}

    def test_empty_graph(self) -> None:
        graph = DependencyGraph()
        assert topological_sort(graph) == []


# ---------------------------------------------------------------------------
# detect_layer
# ---------------------------------------------------------------------------

class TestDetectLayer:
    def test_staging_no_internal_deps(self) -> None:
        graph = DependencyGraph(
            nodes={"stg_orders": None, "mart_orders": None},  # type: ignore[arg-type]
            edges={"stg_orders": set(), "mart_orders": {"stg_orders"}},
        )
        assert detect_layer("stg_orders", graph) == "staging"

    def test_marts_no_dependents(self) -> None:
        graph = DependencyGraph(
            nodes={"stg_orders": None, "mart_orders": None},  # type: ignore[arg-type]
            edges={"stg_orders": set(), "mart_orders": {"stg_orders"}},
        )
        assert detect_layer("mart_orders", graph) == "marts"

    def test_intermediate(self) -> None:
        graph = DependencyGraph(
            nodes={"a": None, "b": None, "c": None},  # type: ignore[arg-type]
            edges={"a": set(), "b": {"a"}, "c": {"b"}},
        )
        # b has internal deps and has dependents -> intermediate
        assert detect_layer("b", graph) == "intermediate"


# ---------------------------------------------------------------------------
# replace_refs_in_sql
# ---------------------------------------------------------------------------

class TestReplaceRefsInSql:
    def test_replace_ref(self) -> None:
        sql = "SELECT * FROM staging.orders"
        result = replace_refs_in_sql(
            sql,
            ref_map={"staging.orders": "stg_orders"},
            source_map={},
        )
        assert "{{ ref('stg_orders') }}" in result
        assert "staging.orders" not in result

    def test_replace_source(self) -> None:
        sql = "SELECT * FROM raw.customers"
        result = replace_refs_in_sql(
            sql,
            ref_map={},
            source_map={"raw.customers": ("raw", "customers")},
        )
        assert "{{ source('raw', 'customers') }}" in result
        assert "raw.customers" not in result

    def test_mixed_refs_and_sources(self) -> None:
        sql = "SELECT * FROM raw.orders o JOIN staging.customers c ON o.id = c.id"
        result = replace_refs_in_sql(
            sql,
            ref_map={"staging.customers": "stg_customers"},
            source_map={"raw.orders": ("raw", "orders")},
        )
        assert "{{ source('raw', 'orders') }}" in result
        assert "{{ ref('stg_customers') }}" in result

    def test_case_insensitive(self) -> None:
        sql = "SELECT * FROM RAW.ORDERS"
        result = replace_refs_in_sql(
            sql,
            ref_map={},
            source_map={"raw.orders": ("raw", "orders")},
        )
        assert "{{ source('raw', 'orders') }}" in result
