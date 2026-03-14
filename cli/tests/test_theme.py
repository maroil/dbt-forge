"""Tests for the centralized UI theme module."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
import questionary
from rich.table import Table

from dbt_forge.ui.theme import (
    ICON_BULLET,
    ICON_FAIL,
    ICON_OK,
    ICON_SKIP,
    ICON_WARN,
    abort,
    forge_style,
    make_table,
    print_debug,
    print_error,
    print_ok,
    print_step,
    print_warning,
    set_verbose,
    timed,
)


class TestForgeStyle:
    def test_returns_questionary_style(self):
        style = forge_style()
        assert isinstance(style, questionary.Style)

    def test_contains_key_rules(self):
        style = forge_style()
        # The style object should have style_rules attribute
        rules = style.style_rules
        rule_names = [name for name, _ in rules]
        assert "qmark" in rule_names
        assert "question" in rule_names
        assert "answer" in rule_names
        assert "pointer" in rule_names
        assert "highlighted" in rule_names
        assert "selected" in rule_names
        assert "checkbox-selected" in rule_names

    def test_selected_is_bold(self):
        style = forge_style()
        rules = dict(style.style_rules)
        assert "bold" in rules["selected"]
        assert "bold" in rules["checkbox-selected"]


class TestMakeTable:
    def test_returns_rich_table(self):
        table = make_table("Test", [("Col1", {}), ("Col2", {"justify": "right"})])
        assert isinstance(table, Table)

    def test_has_title(self):
        table = make_table("My Title", [("A", {})])
        assert table.title == "My Title"

    def test_has_columns(self):
        table = make_table("T", [("Name", {}), ("Value", {"justify": "right"})])
        assert len(table.columns) == 2
        assert table.columns[0].header == "Name"
        assert table.columns[1].header == "Value"


class TestTimed:
    def test_measures_elapsed(self, capsys):
        with patch("dbt_forge.ui.theme.forge_console") as mock_console:
            # Disable the status context manager
            mock_console.status.return_value.__enter__ = lambda s: None
            mock_console.status.return_value.__exit__ = lambda s, *a: None

            with timed("test operation..."):
                time.sleep(0.05)

            # Check that the done message was printed
            calls = mock_console.print.call_args_list
            assert len(calls) > 0
            done_msg = str(calls[-1])
            assert "done in" in done_msg


class TestPrintStep:
    def test_format(self):
        with patch("dbt_forge.ui.theme.forge_console") as mock_console:
            print_step(1, 4, "Project Setup")
            calls = mock_console.print.call_args_list
            # Should contain step number and label
            combined = " ".join(str(c) for c in calls)
            assert "1/4" in combined
            assert "Project Setup" in combined


class TestVerboseToggle:
    def test_debug_silent_when_not_verbose(self):
        set_verbose(False)
        with patch("dbt_forge.ui.theme.forge_console") as mock_console:
            print_debug("should not appear")
            mock_console.print.assert_not_called()

    def test_debug_prints_when_verbose(self):
        set_verbose(True)
        try:
            with patch("dbt_forge.ui.theme.forge_console") as mock_console:
                print_debug("debug message")
                mock_console.print.assert_called_once()
                msg = str(mock_console.print.call_args)
                assert "debug message" in msg
        finally:
            set_verbose(False)


class TestIconConstants:
    def test_all_icons_are_nonempty_strings(self):
        for icon in (ICON_OK, ICON_FAIL, ICON_WARN, ICON_SKIP, ICON_BULLET):
            assert isinstance(icon, str)
            assert len(icon) > 0


class TestAbort:
    def test_raises_exit(self):
        from click.exceptions import Exit

        with patch("dbt_forge.ui.theme.forge_console"):
            with pytest.raises(Exit):
                abort()


class TestPrintHelpers:
    def test_print_ok(self):
        with patch("dbt_forge.ui.theme.forge_console") as mock_console:
            print_ok("All good")
            msg = str(mock_console.print.call_args)
            assert "All good" in msg

    def test_print_error(self):
        with patch("dbt_forge.ui.theme.forge_console") as mock_console:
            print_error("Something broke")
            msg = str(mock_console.print.call_args)
            assert "Something broke" in msg

    def test_print_warning(self):
        with patch("dbt_forge.ui.theme.forge_console") as mock_console:
            print_warning("Caution")
            msg = str(mock_console.print.call_args)
            assert "Caution" in msg
