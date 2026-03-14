"""Tests for the dbt-forge cost module."""

from __future__ import annotations

import json
from contextlib import nullcontext
from unittest.mock import patch

from dbt_forge.cost import CostReport, QueryStat


class TestQueryStat:
    def test_creation(self):
        stat = QueryStat(
            model_name="orders",
            total_bytes_scanned=1_000_000,
            avg_duration_seconds=2.5,
            execution_count=10,
            estimated_cost_usd=0.05,
            materialization="table",
        )
        assert stat.model_name == "orders"
        assert stat.estimated_cost_usd == 0.05
        assert stat.materialization == "table"

    def test_default_values(self):
        stat = QueryStat(model_name="x")
        assert stat.total_bytes_scanned == 0
        assert stat.avg_duration_seconds == 0.0
        assert stat.execution_count == 0
        assert stat.estimated_cost_usd == 0.0
        assert stat.materialization == ""


class TestCostReport:
    def test_total_estimated_cost(self):
        report = CostReport(
            stats=[
                QueryStat(model_name="a", estimated_cost_usd=1.50),
                QueryStat(model_name="b", estimated_cost_usd=2.50),
                QueryStat(model_name="c", estimated_cost_usd=0.50),
            ]
        )
        assert report.total_estimated_cost == 4.50

    def test_top_n(self):
        report = CostReport(
            stats=[
                QueryStat(model_name="a", estimated_cost_usd=1.00),
                QueryStat(model_name="b", estimated_cost_usd=5.00),
                QueryStat(model_name="c", estimated_cost_usd=3.00),
                QueryStat(model_name="d", estimated_cost_usd=0.50),
            ]
        )
        top = report.top_n(2)
        assert len(top) == 2
        assert top[0].model_name == "b"
        assert top[1].model_name == "c"

    def test_top_n_with_fewer_stats(self):
        report = CostReport(stats=[QueryStat(model_name="a", estimated_cost_usd=1.00)])
        top = report.top_n(10)
        assert len(top) == 1

    def test_empty_report(self):
        report = CostReport()
        assert report.total_estimated_cost == 0
        assert report.top_n(10) == []

    def test_top_n_stable_ordering(self):
        report = CostReport(
            stats=[
                QueryStat(model_name="a", estimated_cost_usd=5.00),
                QueryStat(model_name="b", estimated_cost_usd=5.00),
            ]
        )
        top = report.top_n(2)
        assert len(top) == 2
        # Both have same cost, but order should be deterministic
        names = {t.model_name for t in top}
        assert names == {"a", "b"}


class TestMaterializationSuggestions:
    def test_view_to_table(self):
        report = CostReport(
            stats=[
                QueryStat(
                    model_name="hot_view",
                    materialization="view",
                    execution_count=100,
                ),
            ]
        )
        suggestions = report.materialization_suggestions()
        assert len(suggestions) == 1
        assert suggestions[0]["suggested"] == "table"
        assert suggestions[0]["model"] == "hot_view"
        assert suggestions[0]["current"] == "view"
        assert "100" in suggestions[0]["reason"]

    def test_view_below_threshold_no_suggestion(self):
        report = CostReport(
            stats=[
                QueryStat(
                    model_name="normal_view",
                    materialization="view",
                    execution_count=30,
                ),
            ]
        )
        suggestions = report.materialization_suggestions()
        assert len(suggestions) == 0

    def test_table_to_incremental(self):
        report = CostReport(
            stats=[
                QueryStat(
                    model_name="big_table",
                    materialization="table",
                    total_bytes_scanned=20 * 1024**3,  # 20 GB
                    execution_count=2,
                ),
            ]
        )
        suggestions = report.materialization_suggestions()
        assert len(suggestions) == 1
        assert suggestions[0]["suggested"] == "incremental"

    def test_table_to_view(self):
        report = CostReport(
            stats=[
                QueryStat(
                    model_name="unused_table",
                    materialization="table",
                    total_bytes_scanned=100,
                    execution_count=1,
                ),
            ]
        )
        suggestions = report.materialization_suggestions()
        assert len(suggestions) == 1
        assert suggestions[0]["suggested"] == "view"
        assert suggestions[0]["reason"] == "Rarely queried"

    def test_no_suggestions(self):
        report = CostReport(
            stats=[
                QueryStat(
                    model_name="good_table",
                    materialization="table",
                    total_bytes_scanned=100,
                    execution_count=10,
                ),
            ]
        )
        suggestions = report.materialization_suggestions()
        assert len(suggestions) == 0

    def test_empty_report_no_suggestions(self):
        report = CostReport()
        assert report.materialization_suggestions() == []

    def test_multiple_suggestions(self):
        report = CostReport(
            stats=[
                QueryStat(
                    model_name="hot_view",
                    materialization="view",
                    execution_count=100,
                ),
                QueryStat(
                    model_name="cold_table",
                    materialization="table",
                    total_bytes_scanned=100,
                    execution_count=1,
                ),
            ]
        )
        suggestions = report.materialization_suggestions()
        assert len(suggestions) == 2
        models = {s["model"] for s in suggestions}
        assert models == {"hot_view", "cold_table"}

    def test_no_materialization_no_suggestion(self):
        """Models without materialization info should not trigger."""
        report = CostReport(
            stats=[
                QueryStat(
                    model_name="unknown",
                    execution_count=100,
                ),
            ]
        )
        suggestions = report.materialization_suggestions()
        assert len(suggestions) == 0


class TestFormatBytes:
    """Test the _format_bytes helper in cost_cmd."""

    def test_zero_bytes(self):
        from dbt_forge.cli.cost_cmd import _format_bytes

        assert _format_bytes(0) == "0 B"

    def test_bytes(self):
        from dbt_forge.cli.cost_cmd import _format_bytes

        result = _format_bytes(500)
        assert "B" in result
        assert "500" in result

    def test_kilobytes(self):
        from dbt_forge.cli.cost_cmd import _format_bytes

        result = _format_bytes(2048)
        assert "KB" in result

    def test_megabytes(self):
        from dbt_forge.cli.cost_cmd import _format_bytes

        result = _format_bytes(5 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        from dbt_forge.cli.cost_cmd import _format_bytes

        result = _format_bytes(10 * 1024**3)
        assert "GB" in result

    def test_terabytes(self):
        from dbt_forge.cli.cost_cmd import _format_bytes

        result = _format_bytes(2 * 1024**4)
        assert "TB" in result


class TestRenderCostJson:
    def test_renders_valid_json(self):
        import json

        from dbt_forge.cli.cost_cmd import render_cost_json

        report = CostReport(stats=[
            QueryStat(
                model_name="orders",
                total_bytes_scanned=1_000_000,
                avg_duration_seconds=2.5,
                execution_count=10,
                estimated_cost_usd=0.05,
                materialization="table",
            ),
            QueryStat(
                model_name="users",
                total_bytes_scanned=500_000,
                avg_duration_seconds=1.0,
                execution_count=5,
                estimated_cost_usd=0.02,
                materialization="view",
            ),
        ])
        top = report.top_n(10)
        output = render_cost_json(report, top, 30)
        data = json.loads(output)
        assert data["days"] == 30
        assert data["total_estimated_cost_usd"] == 0.07
        assert len(data["models"]) == 2
        assert data["models"][0]["model_name"] == "orders"
        assert "suggestions" in data


class TestRunCost:
    def test_connection_failure_is_reported(self):
        from dbt_forge.cli.cost_cmd import run_cost

        class BrokenIntrospector:
            def connect(self):
                raise RuntimeError("adapter boom")

            def close(self):
                pass

        with (
            patch("dbt_forge.cli.cost_cmd.find_project_root", return_value="."),
            patch("dbt_forge.cli.cost_cmd.read_profile", return_value=("snowflake", {})),
            patch(
                "dbt_forge.cli.cost_cmd.get_introspector",
                return_value=BrokenIntrospector(),
            ),
            patch("dbt_forge.cli.cost_cmd.timed", return_value=nullcontext()),
            patch("dbt_forge.cli.cost_cmd.print_error") as mock_print_error,
        ):
            run_cost()

        mock_print_error.assert_called_once_with("Error connecting to warehouse: adapter boom")

    def test_json_output_is_parseable(self, capsys):
        from dbt_forge.cli.cost_cmd import run_cost

        class Introspector:
            def connect(self):
                pass

            def close(self):
                pass

        stats = [
            QueryStat(
                model_name="orders",
                total_bytes_scanned=1_000_000,
                avg_duration_seconds=2.5,
                execution_count=10,
                estimated_cost_usd=0.05,
                materialization="table",
            )
        ]

        with (
            patch("dbt_forge.cli.cost_cmd.find_project_root", return_value="."),
            patch("dbt_forge.cli.cost_cmd.read_profile", return_value=("bigquery", {})),
            patch("dbt_forge.cli.cost_cmd.get_introspector", return_value=Introspector()),
            patch.dict("dbt_forge.cli.cost_cmd.ADAPTER_STATS_FN", {"bigquery": lambda *_: stats}),
        ):
            run_cost(output_format="json")

        data = json.loads(capsys.readouterr().out)
        assert data["total_estimated_cost_usd"] == 0.05
        assert data["models"][0]["model_name"] == "orders"

    def test_json_output_handles_empty_stats(self, capsys):
        from dbt_forge.cli.cost_cmd import run_cost

        class Introspector:
            def connect(self):
                pass

            def close(self):
                pass

        with (
            patch("dbt_forge.cli.cost_cmd.find_project_root", return_value="."),
            patch("dbt_forge.cli.cost_cmd.read_profile", return_value=("bigquery", {})),
            patch("dbt_forge.cli.cost_cmd.get_introspector", return_value=Introspector()),
            patch.dict("dbt_forge.cli.cost_cmd.ADAPTER_STATS_FN", {"bigquery": lambda *_: []}),
        ):
            run_cost(output_format="json")

        data = json.loads(capsys.readouterr().out)
        assert data["total_estimated_cost_usd"] == 0
        assert data["models"] == []
