"""Tests for the dbt-forge impact command."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from dbt_forge.cli.impact import (
    _build_impact_tree,
    _compute_blast_radius,
    _get_changed_models_from_git,
    _render_pr_markdown,
    run_impact,
)
from dbt_forge.ref_graph import ModelNode, RefEdge, RefGraph


def _make_test_graph() -> RefGraph:
    """Create a test graph: stg_orders -> fct_orders -> rpt_revenue."""
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
        "rpt_revenue": ModelNode(
            name="rpt_revenue",
            sql_path=Path("models/marts/rpt_revenue.sql"),
            layer="marts",
            refs=[RefEdge(model="fct_orders", ref_type="ref")],
        ),
    }
    graph.upstream = {
        "stg_orders": set(),
        "fct_orders": {"stg_orders"},
        "rpt_revenue": {"fct_orders"},
    }
    graph.downstream = {
        "stg_orders": {"fct_orders"},
        "fct_orders": {"rpt_revenue"},
        "rpt_revenue": set(),
    }
    return graph


class TestComputeBlastRadius:
    def test_single_model_impact(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["stg_orders"], set())
        assert blast["total_impacted"] == 2
        assert blast["direct"] == 1
        assert blast["transitive"] == 1

    def test_leaf_model_no_impact(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["rpt_revenue"], set())
        assert blast["total_impacted"] == 0
        assert blast["direct"] == 0
        assert blast["transitive"] == 0

    def test_untested_count(self):
        graph = _make_test_graph()
        tested = {"fct_orders"}
        blast = _compute_blast_radius(graph, ["stg_orders"], tested)
        assert blast["untested_count"] == 1  # rpt_revenue is untested
        assert "rpt_revenue" in blast["untested_models"]

    def test_all_tested(self):
        graph = _make_test_graph()
        tested = {"fct_orders", "rpt_revenue"}
        blast = _compute_blast_radius(graph, ["stg_orders"], tested)
        assert blast["untested_count"] == 0
        assert blast["untested_models"] == []

    def test_blast_percentage(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["stg_orders"], set())
        # 2 impacted out of 3 total = 66.7%
        assert blast["blast_pct"] == 66.7

    def test_multiple_changed_models(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["stg_orders", "fct_orders"], set())
        # stg_orders impacts fct_orders (depth 1), rpt_revenue (depth 2)
        # fct_orders impacts rpt_revenue (depth 1)
        assert blast["total_impacted"] == 2
        # rpt_revenue is direct from fct_orders and transitive from stg_orders
        # direct should count depth==1, transitive depth>1
        assert blast["direct"] >= 1

    def test_empty_changed_list(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, [], set())
        assert blast["total_impacted"] == 0
        assert blast["blast_pct"] == 0

    def test_zero_total_models_no_division_error(self):
        graph = RefGraph()
        blast = _compute_blast_radius(graph, ["anything"], set())
        assert blast["blast_pct"] == 0


class TestBuildImpactTree:
    def test_creates_tree(self):
        graph = _make_test_graph()
        tree = _build_impact_tree(graph, "stg_orders")
        assert tree.label is not None

    def test_tree_has_children(self):
        graph = _make_test_graph()
        tree = _build_impact_tree(graph, "stg_orders")
        # Should have at least one child (fct_orders)
        assert len(tree.children) > 0

    def test_leaf_model_tree_has_no_children(self):
        graph = _make_test_graph()
        tree = _build_impact_tree(graph, "rpt_revenue")
        assert len(tree.children) == 0


class TestRenderPrMarkdown:
    def test_renders_markdown(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["stg_orders"], set())
        md = _render_pr_markdown(graph, ["stg_orders"], blast)
        assert "## Impact Analysis" in md
        assert "`stg_orders`" in md
        assert "Total impacted" in md
        assert "Blast radius" in md
        assert "66.7%" in md

    def test_includes_untested(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["stg_orders"], {"fct_orders"})
        md = _render_pr_markdown(graph, ["stg_orders"], blast)
        assert "Untested impacted models" in md
        assert "`rpt_revenue`" in md

    def test_no_untested_section_when_all_tested(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["stg_orders"], {"fct_orders", "rpt_revenue"})
        md = _render_pr_markdown(graph, ["stg_orders"], blast)
        assert "Untested impacted models" not in md

    def test_multiple_changed_models_listed(self):
        graph = _make_test_graph()
        blast = _compute_blast_radius(graph, ["stg_orders", "fct_orders"], set())
        md = _render_pr_markdown(graph, ["stg_orders", "fct_orders"], blast)
        assert "`stg_orders`" in md
        assert "`fct_orders`" in md


class TestGetChangedModelsFromGit:
    def test_parses_git_output(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "models/staging/stg_orders.sql\n"
            "models/marts/fct_orders.sql\n"
            "models/staging/_stg_orders__models.yml\n"
        )

        with patch("dbt_forge.cli.impact.subprocess.run", return_value=mock_result):
            changed = _get_changed_models_from_git(Path("/tmp/project"), "main")
            assert changed == ["stg_orders", "fct_orders"]

    def test_returns_empty_on_git_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("dbt_forge.cli.impact.subprocess.run", return_value=mock_result):
            changed = _get_changed_models_from_git(Path("/tmp"), "main")
            assert changed == []

    def test_returns_empty_on_no_changes(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("dbt_forge.cli.impact.subprocess.run", return_value=mock_result):
            changed = _get_changed_models_from_git(Path("/tmp"), "main")
            assert changed == []


class TestRunImpact:
    def test_impact_single_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            models = root / "models"
            staging = models / "staging"
            marts = models / "marts"
            staging.mkdir(parents=True)
            marts.mkdir(parents=True)

            (staging / "stg_orders.sql").write_text("SELECT * FROM {{ source('raw', 'orders') }}")
            (marts / "fct_orders.sql").write_text("SELECT * FROM {{ ref('stg_orders') }}")

            with patch("dbt_forge.cli.impact.find_project_root", return_value=root):
                run_impact(model="stg_orders")

    def test_impact_model_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            (root / "models").mkdir()

            with patch("dbt_forge.cli.impact.find_project_root", return_value=root):
                # Should print error, not raise
                run_impact(model="nonexistent")

    def test_impact_no_args_shows_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            (root / "models").mkdir()

            with patch("dbt_forge.cli.impact.find_project_root", return_value=root):
                # Should print error about providing model or --diff
                run_impact(model=None, diff=False)

    def test_impact_pr_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            models = root / "models" / "staging"
            models.mkdir(parents=True)
            (models / "stg_orders.sql").write_text("SELECT 1")

            with patch("dbt_forge.cli.impact.find_project_root", return_value=root):
                run_impact(model="stg_orders", pr=True)

    def test_impact_diff_mode_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            (root / "models").mkdir()

            with (
                patch("dbt_forge.cli.impact.find_project_root", return_value=root),
                patch(
                    "dbt_forge.cli.impact._get_changed_models_from_git",
                    return_value=[],
                ),
            ):
                run_impact(diff=True, base="main")
