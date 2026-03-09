"""Tests for the dbt-forge changelog module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import yaml

from dbt_forge.changelog import (
    ModelChange,
    _detect_column_changes,
    _parse_yml_columns,
    detect_changes_between_refs,
    render_changelog_json,
    render_changelog_markdown,
)


class TestDetectColumnChanges:
    def test_no_changes(self):
        old = {"id": "INTEGER", "name": "VARCHAR"}
        new = {"id": "INTEGER", "name": "VARCHAR"}
        changes = _detect_column_changes("orders", old, new, "abc123", "2024-01-01")
        assert len(changes) == 0

    def test_column_added(self):
        old = {"id": "INTEGER"}
        new = {"id": "INTEGER", "email": "VARCHAR"}
        changes = _detect_column_changes("orders", old, new, "abc123", "2024-01-01")
        assert len(changes) == 1
        assert changes[0].change_type == "column_added"
        assert changes[0].model_name == "orders"
        assert not changes[0].is_breaking
        assert "email" in changes[0].details

    def test_column_removed(self):
        old = {"id": "INTEGER", "email": "VARCHAR"}
        new = {"id": "INTEGER"}
        changes = _detect_column_changes("orders", old, new, "abc123", "2024-01-01")
        assert len(changes) == 1
        assert changes[0].change_type == "column_removed"
        assert changes[0].is_breaking
        assert changes[0].commit_hash == "abc123"
        assert changes[0].commit_date == "2024-01-01"

    def test_type_changed(self):
        old = {"id": "INTEGER"}
        new = {"id": "VARCHAR"}
        changes = _detect_column_changes("orders", old, new, "abc123", "2024-01-01")
        assert len(changes) == 1
        assert changes[0].change_type == "type_changed"
        assert changes[0].is_breaking
        assert "INTEGER" in changes[0].details
        assert "VARCHAR" in changes[0].details

    def test_type_change_ignores_empty(self):
        old = {"id": ""}
        new = {"id": "INTEGER"}
        changes = _detect_column_changes("orders", old, new, "abc123", "2024-01-01")
        assert len(changes) == 0

    def test_both_types_empty_no_change(self):
        old = {"id": ""}
        new = {"id": ""}
        changes = _detect_column_changes("orders", old, new, "abc123", "2024-01-01")
        assert len(changes) == 0

    def test_multiple_changes(self):
        old = {"id": "INTEGER", "name": "VARCHAR", "email": "VARCHAR"}
        new = {"id": "INTEGER", "name": "TEXT", "phone": "VARCHAR"}
        changes = _detect_column_changes("users", old, new, "abc", "2024-01-01")
        assert len(changes) == 3
        types = {c.change_type for c in changes}
        assert types == {"column_removed", "column_added", "type_changed"}
        breaking = [c for c in changes if c.is_breaking]
        assert len(breaking) == 2

    def test_empty_dicts(self):
        changes = _detect_column_changes("m", {}, {}, "", "")
        assert len(changes) == 0

    def test_all_new(self):
        changes = _detect_column_changes("m", {}, {"a": "INT", "b": "TEXT"}, "", "")
        assert len(changes) == 2
        assert all(c.change_type == "column_added" for c in changes)

    def test_all_removed(self):
        changes = _detect_column_changes("m", {"a": "INT", "b": "TEXT"}, {}, "", "")
        assert len(changes) == 2
        assert all(c.change_type == "column_removed" for c in changes)
        assert all(c.is_breaking for c in changes)


class TestParseYmlColumns:
    def test_parses_columns(self):
        content = yaml.dump(
            {
                "models": [
                    {
                        "name": "orders",
                        "columns": [
                            {"name": "id", "data_type": "INTEGER"},
                            {"name": "name", "data_type": "VARCHAR"},
                        ],
                    }
                ]
            }
        )
        cols = _parse_yml_columns(content, "orders")
        assert cols == {"id": "INTEGER", "name": "VARCHAR"}

    def test_missing_model(self):
        content = yaml.dump({"models": [{"name": "other", "columns": [{"name": "id"}]}]})
        cols = _parse_yml_columns(content, "orders")
        assert cols == {}

    def test_missing_data_type(self):
        content = yaml.dump({"models": [{"name": "orders", "columns": [{"name": "id"}]}]})
        cols = _parse_yml_columns(content, "orders")
        assert cols == {"id": ""}

    def test_invalid_yaml(self):
        cols = _parse_yml_columns("{{invalid", "orders")
        assert cols == {}

    def test_empty_content(self):
        cols = _parse_yml_columns("", "orders")
        assert cols == {}


class TestDetectChangesBetweenRefs:
    def test_detects_added_sql_file(self):
        def mock_git_run(root, *args):
            args_str = " ".join(args)
            if "diff --name-status" in args_str:
                return "A\tmodels/staging/stg_new.sql"
            if "log" in args_str:
                return "abc12345 2024-06-01T00:00:00"
            return ""

        with patch("dbt_forge.changelog._git_run", side_effect=mock_git_run):
            changes = detect_changes_between_refs(Path("/tmp"), "v1.0", "HEAD")
            assert len(changes) == 1
            assert changes[0].change_type == "added"
            assert changes[0].model_name == "stg_new"
            assert not changes[0].is_breaking

    def test_detects_deleted_sql_file(self):
        def mock_git_run(root, *args):
            args_str = " ".join(args)
            if "diff --name-status" in args_str:
                return "D\tmodels/staging/stg_old.sql"
            if "log" in args_str:
                return "def456 2024-06-01"
            return ""

        with patch("dbt_forge.changelog._git_run", side_effect=mock_git_run):
            changes = detect_changes_between_refs(Path("/tmp"), "v1.0", "HEAD")
            assert len(changes) == 1
            assert changes[0].change_type == "removed"
            assert changes[0].is_breaking

    def test_detects_modified_sql_file(self):
        def mock_git_run(root, *args):
            args_str = " ".join(args)
            if "diff --name-status" in args_str:
                return "M\tmodels/staging/stg_orders.sql"
            if "log" in args_str:
                return "aaa1111 2024-06-01"
            return ""

        with patch("dbt_forge.changelog._git_run", side_effect=mock_git_run):
            changes = detect_changes_between_refs(Path("/tmp"), "v1.0", "HEAD")
            assert len(changes) == 1
            assert changes[0].change_type == "modified"
            assert not changes[0].is_breaking

    def test_detects_yml_column_changes(self):
        old_yml = yaml.dump(
            {
                "models": [
                    {
                        "name": "orders",
                        "columns": [
                            {"name": "id", "data_type": "INTEGER"},
                            {"name": "old_col", "data_type": "TEXT"},
                        ],
                    }
                ]
            }
        )
        new_yml = yaml.dump(
            {
                "models": [
                    {
                        "name": "orders",
                        "columns": [
                            {"name": "id", "data_type": "INTEGER"},
                            {"name": "new_col", "data_type": "TEXT"},
                        ],
                    }
                ]
            }
        )

        def mock_git_run(root, *args):
            args_str = " ".join(args)
            if "diff --name-status" in args_str:
                return "M\tmodels/staging/_orders.yml"
            if "show" in args_str and "v1.0:" in args_str:
                return old_yml
            if "show" in args_str and "HEAD:" in args_str:
                return new_yml
            if "log" in args_str:
                return "bbb2222 2024-06-01"
            return ""

        with patch("dbt_forge.changelog._git_run", side_effect=mock_git_run):
            changes = detect_changes_between_refs(Path("/tmp"), "v1.0", "HEAD")
            assert len(changes) == 2  # old_col removed, new_col added
            types = {c.change_type for c in changes}
            assert "column_removed" in types
            assert "column_added" in types

    def test_no_changes(self):
        def mock_git_run(root, *args):
            return ""

        with patch("dbt_forge.changelog._git_run", side_effect=mock_git_run):
            changes = detect_changes_between_refs(Path("/tmp"), "v1.0", "HEAD")
            assert changes == []

    def test_mixed_sql_and_yml(self):
        def mock_git_run(root, *args):
            args_str = " ".join(args)
            if "diff --name-status" in args_str:
                return "A\tmodels/stg_x.sql\nM\tmodels/stg_y.sql"
            if "log" in args_str:
                return "ccc333 2024-06-01"
            return ""

        with patch("dbt_forge.changelog._git_run", side_effect=mock_git_run):
            changes = detect_changes_between_refs(Path("/tmp"), "v1.0", "HEAD")
            assert len(changes) == 2


class TestRenderChangelogMarkdown:
    def test_no_changes(self):
        md = render_changelog_markdown([])
        assert "No model changes" in md

    def test_breaking_and_non_breaking(self):
        changes = [
            ModelChange("orders", "removed", "Deleted model", True, "abc123", "2024-01-01"),
            ModelChange("customers", "added", "New model", False, "def456", "2024-01-02"),
        ]
        md = render_changelog_markdown(changes)
        assert "# Changelog" in md
        assert "## Breaking Changes" in md
        assert "## Changes" in md
        assert "**orders**" in md
        assert "**customers**" in md

    def test_only_breaking(self):
        changes = [
            ModelChange("orders", "removed", "Deleted", True, "abc", "2024-01-01"),
        ]
        md = render_changelog_markdown(changes)
        assert "## Breaking Changes" in md
        assert "## Changes" not in md

    def test_only_non_breaking(self):
        changes = [
            ModelChange("orders", "added", "New", False, "abc", "2024-01-01"),
        ]
        md = render_changelog_markdown(changes)
        assert "## Breaking Changes" not in md
        assert "## Changes" in md

    def test_includes_commit_hash(self):
        changes = [
            ModelChange("orders", "modified", "Updated SQL", False, "abc1234", "2024-01-01"),
        ]
        md = render_changelog_markdown(changes)
        assert "`abc1234`" in md

    def test_no_commit_hash(self):
        changes = [
            ModelChange("orders", "modified", "Updated SQL", False, "", ""),
        ]
        md = render_changelog_markdown(changes)
        assert "**orders**" in md


class TestRenderChangelogJson:
    def test_renders_json(self):
        changes = [
            ModelChange("orders", "added", "New model", False, "abc123", "2024-01-01"),
        ]
        result = render_changelog_json(changes)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["model_name"] == "orders"
        assert data[0]["change_type"] == "added"
        assert data[0]["is_breaking"] is False
        assert data[0]["commit_hash"] == "abc123"
        assert data[0]["commit_date"] == "2024-01-01"

    def test_empty_changes(self):
        result = render_changelog_json([])
        data = json.loads(result)
        assert data == []

    def test_all_fields_serialized(self):
        changes = [
            ModelChange("m", "column_removed", "Col 'x' removed", True, "abc", "2024-01-01"),
        ]
        result = render_changelog_json(changes)
        data = json.loads(result)
        item = data[0]
        assert set(item.keys()) == {
            "model_name",
            "change_type",
            "details",
            "is_breaking",
            "commit_hash",
            "commit_date",
        }
