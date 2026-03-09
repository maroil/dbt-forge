"""Tests for the ref_graph module."""

from __future__ import annotations

import tempfile
from pathlib import Path

from dbt_forge.ref_graph import (
    RefGraph,
    build_ref_graph,
    compute_complexity,
    detect_cycles,
    get_all_downstream,
    get_all_upstream,
    parse_refs,
)


class TestParseRefs:
    def test_single_ref(self):
        sql = "SELECT * FROM {{ ref('stg_orders') }}"
        refs = parse_refs(sql)
        assert len(refs) == 1
        assert refs[0].model == "stg_orders"
        assert refs[0].ref_type == "ref"

    def test_double_quoted_ref(self):
        sql = 'SELECT * FROM {{ ref("stg_orders") }}'
        refs = parse_refs(sql)
        assert len(refs) == 1
        assert refs[0].model == "stg_orders"

    def test_cross_project_ref(self):
        sql = "SELECT * FROM {{ ref('analytics', 'dim_customers') }}"
        refs = parse_refs(sql)
        assert len(refs) == 1
        assert refs[0].model == "dim_customers"
        assert refs[0].ref_type == "ref"

    def test_source_ref(self):
        sql = "SELECT * FROM {{ source('raw', 'orders') }}"
        refs = parse_refs(sql)
        assert len(refs) == 1
        assert refs[0].model == "orders"
        assert refs[0].ref_type == "source"
        assert refs[0].source_name == "raw"

    def test_multiple_refs(self):
        sql = """
        SELECT *
        FROM {{ ref('stg_orders') }} o
        JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.id
        LEFT JOIN {{ source('raw', 'payments') }} p ON o.id = p.order_id
        """
        refs = parse_refs(sql)
        assert len(refs) == 3
        ref_names = {r.model for r in refs}
        assert ref_names == {"stg_orders", "stg_customers", "payments"}

    def test_no_duplicates(self):
        sql = """
        SELECT * FROM {{ ref('stg_orders') }}
        UNION ALL
        SELECT * FROM {{ ref('stg_orders') }}
        """
        refs = parse_refs(sql)
        assert len(refs) == 1

    def test_no_refs(self):
        sql = "SELECT 1 AS id"
        refs = parse_refs(sql)
        assert len(refs) == 0

    def test_ref_with_extra_spaces(self):
        sql = "SELECT * FROM {{  ref( 'stg_orders' )  }}"
        refs = parse_refs(sql)
        assert len(refs) == 1
        assert refs[0].model == "stg_orders"

    def test_mixed_ref_and_source_dedup(self):
        """Same table name from ref and source should both be kept."""
        sql = """
        SELECT * FROM {{ ref('orders') }}
        JOIN {{ source('raw', 'orders') }} ON 1=1
        """
        refs = parse_refs(sql)
        assert len(refs) == 2


class TestComputeComplexity:
    def test_simple_query(self):
        sql = "SELECT id, name FROM orders"
        stats = compute_complexity(sql)
        assert stats["cte_count"] == 0
        assert stats["join_count"] == 0
        assert stats["line_count"] == 1

    def test_query_with_ctes_and_joins(self):
        sql = """WITH cte1 AS (
    SELECT * FROM orders
),
cte2 AS (
    SELECT * FROM customers
)
SELECT *
FROM cte1
JOIN cte2 ON cte1.id = cte2.id
LEFT JOIN payments ON cte1.id = payments.order_id"""
        stats = compute_complexity(sql)
        assert stats["cte_count"] == 2
        assert stats["join_count"] == 2
        assert stats["line_count"] == 10

    def test_no_ctes(self):
        sql = "SELECT a.id FROM a JOIN b ON a.id = b.id"
        stats = compute_complexity(sql)
        assert stats["cte_count"] == 0
        assert stats["join_count"] == 1

    def test_multiline_count(self):
        sql = "\n".join(f"SELECT {i}" for i in range(50))
        stats = compute_complexity(sql)
        assert stats["line_count"] == 50


class TestBuildRefGraph:
    def test_builds_graph_from_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            models = root / "models"
            models.mkdir()

            (models / "stg_orders.sql").write_text("SELECT * FROM {{ source('raw', 'orders') }}")
            (models / "fct_orders.sql").write_text("SELECT * FROM {{ ref('stg_orders') }}")
            (models / "dim_customers.sql").write_text("SELECT * FROM {{ ref('stg_orders') }}")

            graph = build_ref_graph(root)

            assert "stg_orders" in graph.nodes
            assert "fct_orders" in graph.nodes
            assert "dim_customers" in graph.nodes
            assert "fct_orders" in graph.downstream.get("stg_orders", set())
            assert "dim_customers" in graph.downstream.get("stg_orders", set())
            assert "stg_orders" in graph.upstream.get("fct_orders", set())

    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            graph = build_ref_graph(root)
            assert len(graph.nodes) == 0

    def test_layer_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            (root / "models" / "staging").mkdir(parents=True)
            (root / "models" / "intermediate").mkdir(parents=True)
            (root / "models" / "marts").mkdir(parents=True)
            (root / "models" / "utils").mkdir(parents=True)

            (root / "models" / "staging" / "stg_a.sql").write_text("SELECT 1")
            (root / "models" / "intermediate" / "int_b.sql").write_text("SELECT 1")
            (root / "models" / "marts" / "fct_c.sql").write_text("SELECT 1")
            (root / "models" / "utils" / "util_d.sql").write_text("SELECT 1")

            graph = build_ref_graph(root)

            assert graph.nodes["stg_a"].layer == "staging"
            assert graph.nodes["int_b"].layer == "intermediate"
            assert graph.nodes["fct_c"].layer == "marts"
            assert graph.nodes["util_d"].layer == "other"

    def test_complexity_fields_populated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            (root / "models").mkdir()
            (root / "models" / "m.sql").write_text("SELECT a.id FROM a JOIN b ON a.id = b.id")

            graph = build_ref_graph(root)
            node = graph.nodes["m"]
            assert node.join_count == 1
            assert node.line_count == 1

    def test_ref_to_nonexistent_model_ignored(self):
        """Refs to models not in the graph should not create edges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            (root / "models").mkdir()
            (root / "models" / "a.sql").write_text("SELECT * FROM {{ ref('missing_model') }}")
            graph = build_ref_graph(root)
            assert graph.upstream["a"] == set()


class TestGetAllDownstream:
    def test_downstream_chain(self):
        graph = RefGraph()
        graph.nodes = {"a": None, "b": None, "c": None}  # type: ignore
        graph.downstream = {"a": {"b"}, "b": {"c"}, "c": set()}
        graph.upstream = {"a": set(), "b": {"a"}, "c": {"b"}}

        result = get_all_downstream(graph, "a")
        assert "b" in result
        assert "c" in result
        assert result["b"] == 1
        assert result["c"] == 2

    def test_no_downstream(self):
        graph = RefGraph()
        graph.nodes = {"a": None}  # type: ignore
        graph.downstream = {"a": set()}
        result = get_all_downstream(graph, "a")
        assert len(result) == 0

    def test_diamond_graph(self):
        """a -> b, a -> c, b -> d, c -> d"""
        graph = RefGraph()
        graph.nodes = {
            "a": None,
            "b": None,
            "c": None,
            "d": None,  # type: ignore
        }
        graph.downstream = {"a": {"b", "c"}, "b": {"d"}, "c": {"d"}, "d": set()}

        result = get_all_downstream(graph, "a")
        assert "b" in result
        assert "c" in result
        assert "d" in result
        assert result["b"] == 1
        assert result["c"] == 1
        assert result["d"] == 2

    def test_nonexistent_model(self):
        """Should return empty dict for model not in graph."""
        graph = RefGraph()
        graph.downstream = {}
        result = get_all_downstream(graph, "nonexistent")
        assert result == {}


class TestGetAllUpstream:
    def test_upstream_chain(self):
        graph = RefGraph()
        graph.nodes = {"a": None, "b": None, "c": None}  # type: ignore
        graph.upstream = {"a": set(), "b": {"a"}, "c": {"b"}}
        graph.downstream = {"a": {"b"}, "b": {"c"}, "c": set()}

        result = get_all_upstream(graph, "c")
        assert "b" in result
        assert "a" in result
        assert result["b"] == 1
        assert result["a"] == 2

    def test_no_upstream(self):
        graph = RefGraph()
        graph.nodes = {"a": None}  # type: ignore
        graph.upstream = {"a": set()}
        result = get_all_upstream(graph, "a")
        assert len(result) == 0

    def test_diamond_upstream(self):
        """d has upstream b and c, both have upstream a."""
        graph = RefGraph()
        graph.nodes = {
            "a": None,
            "b": None,
            "c": None,
            "d": None,  # type: ignore
        }
        graph.upstream = {"a": set(), "b": {"a"}, "c": {"a"}, "d": {"b", "c"}}
        result = get_all_upstream(graph, "d")
        assert "a" in result
        assert "b" in result
        assert "c" in result


class TestDetectCycles:
    def test_no_cycles(self):
        graph = RefGraph()
        graph.nodes = {"a": None, "b": None}  # type: ignore
        graph.downstream = {"a": {"b"}, "b": set()}
        assert detect_cycles(graph) == []

    def test_detects_cycle(self):
        graph = RefGraph()
        graph.nodes = {"a": None, "b": None, "c": None}  # type: ignore
        graph.downstream = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
        cycles = detect_cycles(graph)
        assert len(cycles) > 0
        # Verify the cycle contains all three nodes
        cycle_nodes = set(cycles[0])
        assert {"a", "b", "c"}.issubset(cycle_nodes)

    def test_self_cycle(self):
        graph = RefGraph()
        graph.nodes = {"a": None}  # type: ignore
        graph.downstream = {"a": {"a"}}
        cycles = detect_cycles(graph)
        assert len(cycles) > 0

    def test_no_cycle_in_larger_dag(self):
        graph = RefGraph()
        graph.nodes = {
            "a": None,
            "b": None,
            "c": None,
            "d": None,  # type: ignore
        }
        graph.downstream = {"a": {"b", "c"}, "b": {"d"}, "c": {"d"}, "d": set()}
        assert detect_cycles(graph) == []
