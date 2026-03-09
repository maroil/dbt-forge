"""Tests for AI docs generate command."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from dbt_forge.docs import (
    find_models_needing_docs,
    read_model_sql,
    update_model_descriptions,
)
from dbt_forge.llm.base import GeneratedDescription, LLMProvider


def _create_test_project(tmpdir: str) -> Path:
    """Create a minimal dbt project for testing."""
    root = Path(tmpdir) / "test_project"
    root.mkdir()
    (root / "dbt_project.yml").write_text("name: test_project\n")
    models = root / "models" / "staging"
    models.mkdir(parents=True)

    # Model SQL
    (models / "stg_orders.sql").write_text(
        "select id, amount, status from {{ source('raw', 'orders') }}"
    )

    # Model YAML with missing descriptions
    yml_content = {
        "version": 2,
        "models": [
            {
                "name": "stg_orders",
                "description": "",
                "columns": [
                    {"name": "id", "description": ""},
                    {"name": "amount", "description": ""},
                    {"name": "status", "description": "Order status"},
                ],
            }
        ],
    }
    (models / "_stg_orders__models.yml").write_text(
        yaml.dump(yml_content, default_flow_style=False)
    )

    return root


class TestFindModelsNeedingDocs:
    def test_finds_undocumented_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _create_test_project(tmpdir)
            models = find_models_needing_docs(root)
            assert len(models) == 1
            assert models[0]["model_name"] == "stg_orders"
            assert "id" in models[0]["columns"]
            assert "amount" in models[0]["columns"]

    def test_includes_existing_descriptions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _create_test_project(tmpdir)
            models = find_models_needing_docs(root)
            assert models[0]["existing_descriptions"] == {"status": "Order status"}

    def test_finds_sql_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _create_test_project(tmpdir)
            models = find_models_needing_docs(root)
            assert models[0]["sql_path"] is not None
            assert models[0]["sql_path"].name == "stg_orders.sql"

    def test_skips_fully_documented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "test_project"
            root.mkdir()
            (root / "dbt_project.yml").write_text("name: test_project\n")
            models = root / "models"
            models.mkdir()
            yml = {
                "version": 2,
                "models": [
                    {
                        "name": "fully_documented",
                        "description": "A documented model",
                        "columns": [
                            {"name": "id", "description": "PK"},
                        ],
                    }
                ],
            }
            (models / "_models.yml").write_text(
                yaml.dump(yml, default_flow_style=False)
            )
            results = find_models_needing_docs(root)
            assert len(results) == 0

    def test_no_models_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "empty"
            root.mkdir()
            assert find_models_needing_docs(root) == []


class TestReadModelSql:
    def test_reads_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "model.sql"
            p.write_text("SELECT 1")
            assert read_model_sql(p) == "SELECT 1"

    def test_missing_file(self):
        assert read_model_sql(None) == ""
        assert read_model_sql(Path("/nonexistent/path.sql")) == ""


class TestUpdateModelDescriptions:
    def test_updates_empty_descriptions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "models.yml"
            yml_content = {
                "version": 2,
                "models": [
                    {
                        "name": "stg_orders",
                        "description": "",
                        "columns": [
                            {"name": "id", "description": ""},
                            {"name": "amount", "description": ""},
                            {"name": "status", "description": "Existing desc"},
                        ],
                    }
                ],
            }
            yml_path.write_text(yaml.dump(yml_content, default_flow_style=False))

            update_model_descriptions(
                yml_path=yml_path,
                model_name="stg_orders",
                model_description="Staging orders model",
                column_descriptions={
                    "id": "Primary key",
                    "amount": "Order total in cents",
                    "status": "Should not overwrite",
                },
            )

            data = yaml.safe_load(yml_path.read_text())
            model = data["models"][0]
            assert model["description"] == "Staging orders model"

            col_map = {c["name"]: c["description"] for c in model["columns"]}
            assert col_map["id"] == "Primary key"
            assert col_map["amount"] == "Order total in cents"
            assert col_map["status"] == "Existing desc"  # NOT overwritten

    def test_preserves_existing_model_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "models.yml"
            yml_content = {
                "version": 2,
                "models": [
                    {
                        "name": "stg_orders",
                        "description": "Already documented",
                        "columns": [
                            {"name": "id", "description": ""},
                        ],
                    }
                ],
            }
            yml_path.write_text(yaml.dump(yml_content, default_flow_style=False))

            update_model_descriptions(
                yml_path=yml_path,
                model_name="stg_orders",
                model_description="New description",
                column_descriptions={"id": "PK"},
            )

            data = yaml.safe_load(yml_path.read_text())
            # Model description should NOT be overwritten
            assert data["models"][0]["description"] == "Already documented"
            # Column should be updated since it was empty
            assert data["models"][0]["columns"][0]["description"] == "PK"

    def test_no_matching_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "models.yml"
            yml_content = {
                "version": 2,
                "models": [{"name": "other_model", "description": ""}],
            }
            yml_path.write_text(yaml.dump(yml_content, default_flow_style=False))

            # Should not crash
            update_model_descriptions(
                yml_path=yml_path,
                model_name="stg_orders",
                model_description="Test",
                column_descriptions={},
            )

            data = yaml.safe_load(yml_path.read_text())
            assert data["models"][0]["description"] == ""


# ---------------------------------------------------------------------------
# CLI flow tests with mock provider
# ---------------------------------------------------------------------------


class MockProvider(LLMProvider):
    """Deterministic mock LLM provider for testing."""

    def __init__(self):
        self._call_count = 0

    def name(self) -> str:
        return "MockLLM"

    def generate_descriptions(
        self,
        model_name: str,
        sql: str,
        columns: list[str],
        existing_descriptions: dict[str, str] | None = None,
    ) -> GeneratedDescription:
        self._call_count += 1
        return GeneratedDescription(
            model_name=model_name,
            model_description=f"Generated description for {model_name}",
            column_descriptions={col: f"Desc for {col}" for col in columns},
        )


class TestRunDocsGenerate:
    """End-to-end tests for run_docs_generate with a mock provider."""

    def test_auto_accept_updates_yaml(self):
        """With --yes, descriptions are written without interactive prompts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _create_test_project(tmpdir)
            provider = MockProvider()

            # Patch to avoid project root detection and provider selection
            with patch(
                "dbt_forge.cli.add._find_project_root", return_value=root
            ), patch(
                "dbt_forge.cli.docs_cmd._select_provider", return_value=provider
            ):
                from dbt_forge.cli.docs_cmd import run_docs_generate

                run_docs_generate(auto_accept=True, delay=0)

            # Verify YAML was updated
            yml = root / "models" / "staging" / "_stg_orders__models.yml"
            data = yaml.safe_load(yml.read_text())
            model = data["models"][0]
            assert model["description"] == "Generated description for stg_orders"
            col_map = {c["name"]: c["description"] for c in model["columns"]}
            assert col_map["id"] == "Desc for id"
            assert col_map["amount"] == "Desc for amount"
            # Existing description preserved
            assert col_map["status"] == "Order status"

    def test_single_model_filter(self):
        """--model filters to a specific model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _create_test_project(tmpdir)
            provider = MockProvider()

            with patch(
                "dbt_forge.cli.add._find_project_root", return_value=root
            ), patch(
                "dbt_forge.cli.docs_cmd._select_provider", return_value=provider
            ):
                from dbt_forge.cli.docs_cmd import run_docs_generate

                run_docs_generate(model="stg_orders", auto_accept=True, delay=0)

            assert provider._call_count == 1

    def test_nonexistent_model_no_updates(self):
        """Filtering to a model that doesn't exist produces no updates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _create_test_project(tmpdir)
            provider = MockProvider()

            with patch(
                "dbt_forge.cli.add._find_project_root", return_value=root
            ), patch(
                "dbt_forge.cli.docs_cmd._select_provider", return_value=provider
            ):
                from dbt_forge.cli.docs_cmd import run_docs_generate

                run_docs_generate(model="nonexistent_model", auto_accept=True, delay=0)

            assert provider._call_count == 0

    def test_fully_documented_project_no_calls(self):
        """When all models are documented, the provider is never called."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "test_project"
            root.mkdir()
            (root / "dbt_project.yml").write_text("name: test_project\n")
            models = root / "models"
            models.mkdir()
            yml = {
                "version": 2,
                "models": [
                    {
                        "name": "complete",
                        "description": "Done",
                        "columns": [{"name": "id", "description": "PK"}],
                    }
                ],
            }
            (models / "_models.yml").write_text(
                yaml.dump(yml, default_flow_style=False)
            )

            provider = MockProvider()
            with patch(
                "dbt_forge.cli.add._find_project_root", return_value=root
            ), patch(
                "dbt_forge.cli.docs_cmd._select_provider", return_value=provider
            ):
                from dbt_forge.cli.docs_cmd import run_docs_generate

                run_docs_generate(auto_accept=True, delay=0)

            assert provider._call_count == 0

    def test_provider_error_skips_model(self):
        """If the provider raises, the model is skipped, not crashed."""

        class FailingProvider(LLMProvider):
            def __init__(self):
                self._call_count = 0

            def name(self):
                return "FailingLLM"

            def generate_descriptions(self, model_name, sql, columns, existing_descriptions=None):
                self._call_count += 1
                raise RuntimeError("API error")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = _create_test_project(tmpdir)
            provider = FailingProvider()

            with patch(
                "dbt_forge.cli.add._find_project_root", return_value=root
            ), patch(
                "dbt_forge.cli.docs_cmd._select_provider", return_value=provider
            ):
                from dbt_forge.cli.docs_cmd import run_docs_generate

                # Should not raise
                run_docs_generate(auto_accept=True, delay=0)

            assert provider._call_count == 1
            # YAML should remain unchanged
            yml = root / "models" / "staging" / "_stg_orders__models.yml"
            data = yaml.safe_load(yml.read_text())
            assert data["models"][0]["description"] == ""

    def test_multiple_models(self):
        """Processes multiple undocumented models in a single run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "test_project"
            root.mkdir()
            (root / "dbt_project.yml").write_text("name: test_project\n")
            models = root / "models"
            models.mkdir()

            yml = {
                "version": 2,
                "models": [
                    {
                        "name": "model_a",
                        "description": "",
                        "columns": [{"name": "id", "description": ""}],
                    },
                    {
                        "name": "model_b",
                        "description": "",
                        "columns": [{"name": "name", "description": ""}],
                    },
                ],
            }
            (models / "_models.yml").write_text(
                yaml.dump(yml, default_flow_style=False)
            )

            provider = MockProvider()
            with patch(
                "dbt_forge.cli.add._find_project_root", return_value=root
            ), patch(
                "dbt_forge.cli.docs_cmd._select_provider", return_value=provider
            ):
                from dbt_forge.cli.docs_cmd import run_docs_generate

                run_docs_generate(auto_accept=True, delay=0)

            assert provider._call_count == 2
            data = yaml.safe_load((models / "_models.yml").read_text())
            assert data["models"][0]["description"] == "Generated description for model_a"
            assert data["models"][1]["description"] == "Generated description for model_b"
