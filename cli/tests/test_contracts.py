"""Tests for the dbt-forge contracts module."""

from __future__ import annotations

import tempfile
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from dbt_forge.contracts import (
    ContractColumn,
    find_public_models,
    generate_contract,
    get_model_schema,
    introspect_model_columns,
)
from dbt_forge.introspect.base import ColumnMetadata


class TestGenerateContract:
    def test_creates_new_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "_orders__models.yml"
            columns = [
                ContractColumn(name="id", data_type="INTEGER", is_nullable=False),
                ContractColumn(name="name", data_type="VARCHAR", is_nullable=True),
                ContractColumn(name="amount", data_type="NUMERIC", is_nullable=True),
            ]
            content = generate_contract(yml_path, "orders", columns)
            data = yaml.safe_load(content)

            assert data["models"][0]["name"] == "orders"
            assert data["models"][0]["config"]["contract"]["enforced"] is True

            cols = data["models"][0]["columns"]
            assert len(cols) == 3
            assert cols[0]["name"] == "id"
            assert cols[0]["data_type"] == "INTEGER"
            assert "not_null" in cols[0]["data_tests"]
            # Nullable columns should not have not_null test
            assert "data_tests" not in cols[1] or "not_null" not in cols[1].get("data_tests", [])

    def test_preserves_existing_descriptions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "_orders__models.yml"
            existing = {
                "version": 2,
                "models": [
                    {
                        "name": "orders",
                        "columns": [
                            {
                                "name": "id",
                                "description": "Primary key",
                                "data_tests": ["unique"],
                            }
                        ],
                    }
                ],
            }
            yml_path.write_text(yaml.dump(existing))

            columns = [
                ContractColumn(name="id", data_type="INTEGER", is_nullable=False),
                ContractColumn(name="name", data_type="VARCHAR", is_nullable=True),
            ]
            content = generate_contract(yml_path, "orders", columns)
            data = yaml.safe_load(content)

            id_col = data["models"][0]["columns"][0]
            assert id_col["description"] == "Primary key"
            assert "unique" in id_col["data_tests"]
            assert "not_null" in id_col["data_tests"]

    def test_preserves_existing_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "_orders__models.yml"
            existing = {
                "version": 2,
                "models": [
                    {
                        "name": "orders",
                        "columns": [
                            {"name": "id", "data_tests": ["unique", "not_null"]},
                        ],
                    }
                ],
            }
            yml_path.write_text(yaml.dump(existing))

            columns = [
                ContractColumn(name="id", data_type="INTEGER", is_nullable=False),
            ]
            content = generate_contract(yml_path, "orders", columns)
            data = yaml.safe_load(content)

            id_col = data["models"][0]["columns"][0]
            assert id_col["data_tests"].count("not_null") == 1

    def test_creates_yml_when_not_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "new_model.yml"
            columns = [
                ContractColumn(name="id", data_type="INTEGER", is_nullable=False),
            ]
            content = generate_contract(yml_path, "new_model", columns)
            data = yaml.safe_load(content)
            assert data["version"] == 2
            assert data["models"][0]["name"] == "new_model"
            assert data["models"][0]["config"]["contract"]["enforced"] is True

    def test_all_nullable_columns(self):
        """All nullable columns should not get not_null tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "m.yml"
            columns = [
                ContractColumn(name="a", data_type="TEXT", is_nullable=True),
                ContractColumn(name="b", data_type="INT", is_nullable=True),
            ]
            content = generate_contract(yml_path, "m", columns)
            data = yaml.safe_load(content)
            for col in data["models"][0]["columns"]:
                assert "data_tests" not in col or "not_null" not in col.get("data_tests", [])

    def test_all_non_nullable_columns(self):
        """All non-nullable columns should get not_null tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "m.yml"
            columns = [
                ContractColumn(name="a", data_type="TEXT", is_nullable=False),
                ContractColumn(name="b", data_type="INT", is_nullable=False),
            ]
            content = generate_contract(yml_path, "m", columns)
            data = yaml.safe_load(content)
            for col in data["models"][0]["columns"]:
                assert "not_null" in col["data_tests"]

    def test_adds_to_existing_model_in_multi_model_yml(self):
        """Should only modify the target model, not others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "models.yml"
            existing = {
                "version": 2,
                "models": [
                    {"name": "other_model", "columns": [{"name": "x"}]},
                    {"name": "orders", "columns": [{"name": "id"}]},
                ],
            }
            yml_path.write_text(yaml.dump(existing))

            columns = [
                ContractColumn(name="id", data_type="INT", is_nullable=False),
            ]
            content = generate_contract(yml_path, "orders", columns)
            data = yaml.safe_load(content)
            # other_model should be untouched
            assert data["models"][0]["name"] == "other_model"
            assert "config" not in data["models"][0]
            # orders should have contract
            assert data["models"][1]["config"]["contract"]["enforced"] is True

    def test_existing_description_from_contract_column(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = Path(tmpdir) / "m.yml"
            columns = [
                ContractColumn(
                    name="id",
                    data_type="INT",
                    is_nullable=False,
                    existing_description="The primary key",
                ),
            ]
            content = generate_contract(yml_path, "m", columns)
            data = yaml.safe_load(content)
            assert data["models"][0]["columns"][0]["description"] == "The primary key"


class TestIntrospectModelColumns:
    def test_converts_column_metadata(self):
        mock_introspector = MagicMock()
        mock_introspector.get_columns.return_value = [
            ColumnMetadata(name="id", data_type="INTEGER", is_nullable=False),
            ColumnMetadata(name="name", data_type="VARCHAR", is_nullable=True, comment="Name"),
        ]

        result = introspect_model_columns(mock_introspector, "public", "orders")
        assert len(result) == 2
        assert result[0].name == "id"
        assert result[0].data_type == "INTEGER"
        assert not result[0].is_nullable
        assert result[1].name == "name"
        assert result[1].is_nullable

    def test_empty_columns(self):
        mock_introspector = MagicMock()
        mock_introspector.get_columns.return_value = []

        result = introspect_model_columns(mock_introspector, "public", "orders")
        assert result == []


class TestGetModelSchema:
    def test_infers_schema_from_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: my_project")
            staging = root / "models" / "staging"
            staging.mkdir(parents=True)
            (staging / "stg_orders.sql").write_text("SELECT 1")

            schema = get_model_schema(root, "stg_orders")
            assert schema == "staging"

    def test_returns_project_name_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: my_project")
            (root / "models").mkdir()
            # Model in root models/ dir (no subfolder)
            (root / "models" / "flat_model.sql").write_text("SELECT 1")

            schema = get_model_schema(root, "flat_model")
            assert schema == "my_project"

    def test_returns_none_without_dbt_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            schema = get_model_schema(root, "anything")
            assert schema is None

    def test_model_not_found_returns_project_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: my_project")
            (root / "models").mkdir()

            schema = get_model_schema(root, "nonexistent")
            assert schema == "my_project"


class TestFindPublicModels:
    def test_finds_public_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            models = root / "models"
            models.mkdir()

            yml = {
                "models": [
                    {"name": "public_model", "access": "public", "columns": []},
                    {"name": "private_model", "columns": []},
                ]
            }
            (models / "_models.yml").write_text(yaml.dump(yml))

            result = find_public_models(root)
            assert "public_model" in result
            assert "private_model" not in result


class TestRunContractsGenerate:
    def test_connection_failure_is_reported(self):
        from dbt_forge.cli.contracts_cmd import run_contracts_generate

        class BrokenIntrospector:
            def connect(self):
                raise RuntimeError("adapter boom")

            def close(self):
                pass

        with (
            patch("dbt_forge.cli.contracts_cmd.find_project_root", return_value="."),
            patch("dbt_forge.cli.contracts_cmd.read_profile", return_value=("snowflake", {})),
            patch(
                "dbt_forge.cli.contracts_cmd.get_introspector",
                return_value=BrokenIntrospector(),
            ),
            patch("dbt_forge.cli.contracts_cmd.timed", return_value=nullcontext()),
            patch("dbt_forge.cli.contracts_cmd.print_error") as mock_print_error,
        ):
            run_contracts_generate(model="orders")

        mock_print_error.assert_called_once_with("Error connecting to warehouse: adapter boom")

    def test_finds_public_in_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            models = root / "models"
            models.mkdir()

            yml = {
                "models": [
                    {
                        "name": "config_public",
                        "config": {"access": "public"},
                        "columns": [],
                    },
                ]
            }
            (models / "_models.yml").write_text(yaml.dump(yml))

            result = find_public_models(root)
            assert "config_public" in result

    def test_no_public_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            models = root / "models"
            models.mkdir()

            yml = {"models": [{"name": "private_model", "columns": []}]}
            (models / "_models.yml").write_text(yaml.dump(yml))

            result = find_public_models(root)
            assert len(result) == 0

    def test_empty_models_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dbt_project.yml").write_text("name: test")
            (root / "models").mkdir()

            result = find_public_models(root)
            assert result == []
