"""Tests for the dbt-forge lint command."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from dbt_forge.cli.lint import (
    _extract_select_columns,
    check_circular_deps,
    check_dag_fan_out,
    check_duplicate_logic,
    check_model_complexity,
    check_source_to_mart,
    check_yaml_sql_drift,
    render_lint_json,
)
from dbt_forge.lint_config import LintConfig, load_lint_config
from dbt_forge.ref_graph import ModelNode, RefEdge, RefGraph


def _make_project(tmpdir: str) -> Path:
    root = Path(tmpdir)
    (root / "dbt_project.yml").write_text("name: test")
    (root / "models").mkdir()
    (root / "models" / "staging").mkdir()
    (root / "models" / "marts").mkdir()
    return root


class TestLintConfig:
    def test_default_config(self):
        config = LintConfig()
        assert config.fan_out_threshold == 5
        assert config.max_cte_count == 8
        assert config.max_join_count == 6
        assert config.max_line_count == 300
        assert config.disabled_rules == []

    def test_load_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".dbt-forge-lint.yml"
            config_path.write_text(
                yaml.dump(
                    {
                        "fan_out_threshold": 3,
                        "max_cte_count": 5,
                        "disabled_rules": ["fan-out"],
                    }
                )
            )
            config = load_lint_config(config_path=config_path)
            assert config.fan_out_threshold == 3
            assert config.max_cte_count == 5
            assert "fan-out" in config.disabled_rules

    def test_load_auto_discover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / ".dbt-forge-lint.yml"
            config_path.write_text(yaml.dump({"fan_out_threshold": 10}))
            config = load_lint_config(root=root)
            assert config.fan_out_threshold == 10

    def test_missing_file_returns_defaults(self):
        config = load_lint_config(config_path=Path("/nonexistent.yml"))
        assert config.fan_out_threshold == 5

    def test_invalid_yaml_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".dbt-forge-lint.yml"
            config_path.write_text("not: [valid: yaml: {{")
            config = load_lint_config(config_path=config_path)
            assert config.fan_out_threshold == 5

    def test_non_dict_yaml_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".dbt-forge-lint.yml"
            config_path.write_text("just a string")
            config = load_lint_config(config_path=config_path)
            assert config.fan_out_threshold == 5


class TestCheckDagFanOut:
    def test_passes_below_threshold(self):
        graph = RefGraph()
        graph.nodes = {"a": None, "b": None}  # type: ignore
        graph.downstream = {"a": {"b"}, "b": set()}
        config = LintConfig(fan_out_threshold=5)
        result = check_dag_fan_out(graph, config)
        assert result.passed

    def test_fails_above_threshold(self):
        graph = RefGraph()
        children = {f"child_{i}" for i in range(6)}
        graph.nodes = {"hub": None}  # type: ignore
        graph.nodes.update({c: None for c in children})  # type: ignore
        graph.downstream = {"hub": children}
        graph.downstream.update({c: set() for c in children})
        config = LintConfig(fan_out_threshold=5)
        result = check_dag_fan_out(graph, config)
        assert not result.passed
        assert "hub" in result.message
        assert "6 downstream" in result.message

    def test_exact_threshold_fails(self):
        graph = RefGraph()
        children = {f"child_{i}" for i in range(5)}
        graph.nodes = {"hub": None}  # type: ignore
        graph.nodes.update({c: None for c in children})  # type: ignore
        graph.downstream = {"hub": children}
        graph.downstream.update({c: set() for c in children})
        config = LintConfig(fan_out_threshold=5)
        result = check_dag_fan_out(graph, config)
        assert not result.passed

    def test_empty_graph_passes(self):
        graph = RefGraph()
        config = LintConfig(fan_out_threshold=5)
        result = check_dag_fan_out(graph, config)
        assert result.passed


class TestCheckSourceToMart:
    def test_passes_with_staging_layer(self):
        graph = RefGraph()
        graph.nodes = {
            "stg_orders": ModelNode(
                name="stg_orders",
                sql_path=Path("models/staging/stg_orders.sql"),
                layer="staging",
                refs=[RefEdge(model="orders", ref_type="source", source_name="raw")],
            ),
            "fct_orders": ModelNode(
                name="fct_orders",
                sql_path=Path("models/marts/fct_orders.sql"),
                layer="marts",
                refs=[RefEdge(model="stg_orders", ref_type="ref")],
            ),
        }
        result = check_source_to_mart(graph)
        assert result.passed

    def test_fails_when_mart_refs_source(self):
        graph = RefGraph()
        graph.nodes = {
            "fct_orders": ModelNode(
                name="fct_orders",
                sql_path=Path("models/marts/fct_orders.sql"),
                layer="marts",
                refs=[RefEdge(model="orders", ref_type="source", source_name="raw")],
            ),
        }
        result = check_source_to_mart(graph)
        assert not result.passed
        assert "fct_orders" in result.message
        assert "source" in result.message.lower()

    def test_staging_refs_source_passes(self):
        """Staging models referencing sources is expected behavior."""
        graph = RefGraph()
        graph.nodes = {
            "stg_orders": ModelNode(
                name="stg_orders",
                sql_path=Path("models/staging/stg_orders.sql"),
                layer="staging",
                refs=[RefEdge(model="orders", ref_type="source", source_name="raw")],
            ),
        }
        result = check_source_to_mart(graph)
        assert result.passed


class TestCheckModelComplexity:
    def test_passes_simple_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text("SELECT 1 AS id")
            config = LintConfig()
            result = check_model_complexity(root, config)
            assert result.passed

    def test_fails_join_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            sql = "SELECT * FROM a\n" + "\n".join(f"JOIN t{i} ON a.id = t{i}.id" for i in range(10))
            (root / "models" / "staging" / "stg_complex.sql").write_text(sql)
            config = LintConfig(max_join_count=5)
            result = check_model_complexity(root, config)
            assert not result.passed
            assert "JOINs=" in result.message

    def test_fails_line_count_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            sql = "\n".join(f"-- line {i}" for i in range(350))
            sql += "\nSELECT 1"
            (root / "models" / "staging" / "stg_long.sql").write_text(sql)
            config = LintConfig(max_line_count=300)
            result = check_model_complexity(root, config)
            assert not result.passed
            assert "lines=" in result.message

    def test_empty_models_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            config = LintConfig()
            result = check_model_complexity(root, config)
            assert result.passed


class TestCheckDuplicateLogic:
    def test_passes_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_a.sql").write_text(
                "WITH cte AS (SELECT id, name, email FROM customers WHERE active = true) "
                "SELECT * FROM cte"
            )
            (root / "models" / "staging" / "stg_b.sql").write_text(
                "WITH cte AS (SELECT id, status, amount FROM orders WHERE completed = true) "
                "SELECT * FROM cte"
            )
            result = check_duplicate_logic(root)
            assert result.passed

    def test_fails_with_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            cte_body = (
                "SELECT id, name, email, status "
                "FROM customers WHERE is_active = true "
                "AND created_at > '2024-01-01'"
            )
            sql_a = (
                f"WITH shared AS ({cte_body}), final AS (SELECT * FROM shared) SELECT * FROM final"
            )
            sql_b = (
                f"WITH shared AS ({cte_body}), "
                "result AS (SELECT * FROM shared) SELECT * FROM result"
            )
            (root / "models" / "staging" / "stg_a.sql").write_text(sql_a)
            (root / "models" / "staging" / "stg_b.sql").write_text(sql_b)
            result = check_duplicate_logic(root)
            assert not result.passed
            assert "stg_a.shared" in result.message
            assert "stg_b.shared" in result.message

    def test_ignores_trivial_ctes(self):
        """CTEs with body shorter than 30 chars should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_a.sql").write_text(
                "WITH cte AS (SELECT 1 AS id), final AS (SELECT * FROM cte) SELECT * FROM final"
            )
            (root / "models" / "staging" / "stg_b.sql").write_text(
                "WITH cte AS (SELECT 1 AS id), final AS (SELECT * FROM cte) SELECT * FROM final"
            )
            result = check_duplicate_logic(root)
            assert result.passed


class TestCheckCircularDeps:
    def test_passes_no_cycles(self):
        graph = RefGraph()
        graph.nodes = {"a": None, "b": None}  # type: ignore
        graph.downstream = {"a": {"b"}, "b": set()}
        result = check_circular_deps(graph)
        assert result.passed

    def test_fails_with_cycle(self):
        graph = RefGraph()
        graph.nodes = {"a": None, "b": None, "c": None}  # type: ignore
        graph.downstream = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
        result = check_circular_deps(graph)
        assert not result.passed
        assert "circular" in result.message.lower()


class TestCheckYamlSqlDrift:
    def test_passes_when_in_sync(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text(
                "SELECT id, name, amount FROM source"
            )
            yml = {
                "models": [
                    {
                        "name": "stg_orders",
                        "columns": [
                            {"name": "id"},
                            {"name": "name"},
                            {"name": "amount"},
                        ],
                    }
                ]
            }
            (root / "models" / "staging" / "_stg_orders__models.yml").write_text(yaml.dump(yml))
            result = check_yaml_sql_drift(root)
            assert result.passed

    def test_fails_when_drifted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text(
                "SELECT id, name, amount FROM source"
            )
            yml = {
                "models": [
                    {
                        "name": "stg_orders",
                        "columns": [
                            {"name": "id"},
                            {"name": "name"},
                            {"name": "old_column"},
                        ],
                    }
                ]
            }
            (root / "models" / "staging" / "_stg_orders__models.yml").write_text(yaml.dump(yml))
            result = check_yaml_sql_drift(root)
            assert not result.passed
            assert "old_column" in result.message or "amount" in result.message

    def test_skips_models_without_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text("SELECT id FROM source")
            yml = {"models": [{"name": "stg_orders", "columns": []}]}
            (root / "models" / "staging" / "_stg_orders__models.yml").write_text(yaml.dump(yml))
            result = check_yaml_sql_drift(root)
            assert result.passed

    def test_skips_sql_without_select(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text("-- just a comment")
            yml = {
                "models": [
                    {
                        "name": "stg_orders",
                        "columns": [{"name": "id"}],
                    }
                ]
            }
            (root / "models" / "staging" / "_stg_orders__models.yml").write_text(yaml.dump(yml))
            result = check_yaml_sql_drift(root)
            assert result.passed


class TestExtractSelectColumns:
    def test_simple_columns(self):
        sql = "SELECT id, name, amount FROM orders"
        cols = _extract_select_columns(sql)
        assert cols == {"id", "name", "amount"}

    def test_aliased_columns(self):
        sql = "SELECT o.id AS order_id, c.name AS customer_name FROM orders o"
        cols = _extract_select_columns(sql)
        assert "order_id" in cols
        assert "customer_name" in cols

    def test_with_cte_uses_final_select(self):
        sql = """
        WITH cte AS (
            SELECT internal_col FROM raw
        )
        SELECT id, name FROM cte
        """
        cols = _extract_select_columns(sql)
        assert "id" in cols
        assert "name" in cols
        # internal_col from inner select should not appear
        assert "internal_col" not in cols

    def test_strips_comments(self):
        sql = """
        -- this is a comment
        SELECT id, /* inline */ name FROM orders
        """
        cols = _extract_select_columns(sql)
        assert "id" in cols
        assert "name" in cols

    def test_no_select_returns_empty(self):
        sql = "-- just a comment"
        cols = _extract_select_columns(sql)
        assert cols == set()

    def test_table_qualified_columns(self):
        sql = "SELECT orders.id, orders.amount FROM orders"
        cols = _extract_select_columns(sql)
        assert "id" in cols
        assert "amount" in cols

    def test_case_insensitive(self):
        sql = "SELECT Id, Name FROM orders"
        cols = _extract_select_columns(sql)
        assert "id" in cols
        assert "name" in cols


class TestLintCli:
    def test_lint_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text(
                "SELECT * FROM {{ ref('stg_customers') }}"
            )
            with patch("dbt_forge.cli.lint.find_project_root", return_value=root):
                from dbt_forge.cli.lint import run_lint

                results = run_lint()
                assert isinstance(results, list)
                assert len(results) == 6  # All 6 rules

    def test_lint_single_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text("SELECT 1")
            with patch("dbt_forge.cli.lint.find_project_root", return_value=root):
                from dbt_forge.cli.lint import run_lint

                results = run_lint(rule="circular-deps")
                assert len(results) == 1
                assert results[0].name == "circular-deps"

    def test_lint_with_disabled_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text("SELECT 1")
            config_path = root / ".dbt-forge-lint.yml"
            config_path.write_text(yaml.dump({"disabled_rules": ["fan-out", "source-to-mart"]}))
            with patch("dbt_forge.cli.lint.find_project_root", return_value=root):
                from dbt_forge.cli.lint import run_lint

                results = run_lint()
                rule_names = {r.name for r in results}
                assert "fan-out" not in rule_names
                assert "source-to-mart" not in rule_names
                assert len(results) == 4  # 6 total - 2 disabled

    def test_lint_with_config_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text("SELECT 1")
            custom_config = Path(tmpdir) / "custom-lint.yml"
            custom_config.write_text(yaml.dump({"fan_out_threshold": 99}))
            with patch("dbt_forge.cli.lint.find_project_root", return_value=root):
                from dbt_forge.cli.lint import run_lint

                results = run_lint(config_path=str(custom_config))
                assert len(results) > 0

    def test_lint_json_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            (root / "models" / "staging" / "stg_orders.sql").write_text("SELECT 1")
            with patch("dbt_forge.cli.lint.find_project_root", return_value=root):
                from dbt_forge.cli.lint import run_lint

                results = run_lint(output_format="json")
                assert len(results) == 6


class TestRenderLintJson:
    def test_renders_valid_json(self):
        from dbt_forge.cli.doctor import CheckResult

        results = [
            CheckResult(name="rule-a", passed=True, message="OK."),
            CheckResult(name="rule-b", passed=False, message="Bad.", fix_hint="Fix."),
        ]
        output = render_lint_json(results)
        data = json.loads(output)
        assert data["passed"] is False
        assert data["pass_count"] == 1
        assert data["warning_count"] == 1
        assert len(data["results"]) == 2
