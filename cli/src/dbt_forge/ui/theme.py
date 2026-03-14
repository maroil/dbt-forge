"""Centralized UI theme for dbt-forge — single source of truth for styling."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Console singleton
# ---------------------------------------------------------------------------

forge_console = Console()

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

ACCENT = "#00d7ff"
SUCCESS = "green"
ERROR = "red"
WARNING = "yellow"
MUTED = "dim"

# ---------------------------------------------------------------------------
# Status icons (with Rich markup)
# ---------------------------------------------------------------------------

ICON_OK = f"[{SUCCESS}]\u2714[/{SUCCESS}]"
ICON_FAIL = f"[{ERROR}]\u2718[/{ERROR}]"
ICON_WARN = f"[{WARNING}]\u26a0[/{WARNING}]"
ICON_SKIP = f"[{MUTED}]\u2014[/{MUTED}]"
ICON_BULLET = f"[{ACCENT}]\u2022[/{ACCENT}]"


# ---------------------------------------------------------------------------
# questionary style
# ---------------------------------------------------------------------------


def forge_style() -> questionary.Style:
    """Return the shared questionary style — replaces all local ``_style()`` functions."""
    return questionary.Style(
        [
            ("qmark", f"fg:{ACCENT} bold"),
            ("question", "bold"),
            ("answer", f"fg:{ACCENT} bold"),
            ("pointer", f"fg:{ACCENT} bold"),
            ("highlighted", f"fg:{ACCENT} bold"),
            ("selected", f"fg:{ACCENT} bold"),
            ("checkbox-selected", f"fg:{ACCENT} bold"),
            ("text", ""),
            ("separator", "fg:#6c6c6c"),
            ("instruction", "fg:#6c6c6c"),
        ]
    )


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------


def print_banner(subtitle: str = "") -> None:
    """Print the dbt-forge banner with optional subtitle."""
    from dbt_forge import __version__

    title = Text()
    title.append("\u2726  dbt-forge", style=f"bold {ACCENT}")
    title.append(f" v{__version__}", style=MUTED)
    if subtitle:
        title.append(f" \u2014 {subtitle}", style=MUTED)

    forge_console.print()
    forge_console.print(
        Panel(title, border_style=ACCENT, expand=False, padding=(0, 1))
    )
    forge_console.print()


def print_section(title: str) -> None:
    """Print a styled section header using a Rule."""
    forge_console.print(Rule(title, style=MUTED))


def print_step(current: int, total: int, label: str) -> None:
    """Print a step indicator: ``[1/4] Project Setup``."""
    forge_console.print()
    forge_console.print(
        f"  [{ACCENT}]\\[{current}/{total}][/{ACCENT}] [bold]{label}[/bold]"
    )
    forge_console.print(Rule(style=MUTED))


def print_ok(msg: str) -> None:
    """Print a success-prefixed message."""
    forge_console.print(f"  {ICON_OK}  {msg}")


def print_error(msg: str) -> None:
    """Print an error-prefixed message."""
    forge_console.print(f"  {ICON_FAIL}  [{ERROR}]{msg}[/{ERROR}]")


def print_warning(msg: str) -> None:
    """Print a warning-prefixed message."""
    forge_console.print(f"  {ICON_WARN}  [{WARNING}]{msg}[/{WARNING}]")


def print_summary(title: str, items: list[str]) -> None:
    """Print a summary panel with a title and bullet items."""
    body = "\n".join(f"  {ICON_BULLET} {item}" for item in items)
    forge_console.print()
    forge_console.print(
        Panel(
            f"[bold]{title}[/bold]\n\n{body}",
            border_style=ACCENT,
            padding=(0, 1),
            expand=False,
        )
    )
    forge_console.print()


def make_table(title: str, columns: list[tuple[str, dict]]) -> Table:
    """Factory for consistently-styled Rich tables.

    *columns* is a list of ``(name, kwargs)`` tuples passed to ``add_column``.
    """
    table = Table(
        title=title,
        show_lines=False,
        padding=(0, 1),
        title_style=f"bold {ACCENT}",
        border_style=MUTED,
    )
    for col_name, col_kwargs in columns:
        table.add_column(col_name, **col_kwargs)
    return table


@contextmanager
def timed(label: str) -> Generator[None, None, None]:
    """Context manager: show a spinner while running, then print elapsed time."""
    start = time.perf_counter()
    with forge_console.status(f"[{ACCENT}]{label}[/{ACCENT}]"):
        yield
    elapsed = time.perf_counter() - start
    forge_console.print(f"  [{MUTED}]{label} done in {elapsed:.1f}s[/{MUTED}]")


def abort() -> None:
    """Centralized abort handler."""
    forge_console.print(f"\n[{MUTED}]Aborted.[/{MUTED}]")
    raise typer.Exit()


# ---------------------------------------------------------------------------
# Verbose / debug output
# ---------------------------------------------------------------------------

_verbose = False


def set_verbose(v: bool) -> None:
    """Toggle verbose mode."""
    global _verbose
    _verbose = v


def print_debug(msg: str) -> None:
    """Print a debug message only when verbose mode is active."""
    if _verbose:
        forge_console.print(f"  [{MUTED}][debug] {msg}[/{MUTED}]")
