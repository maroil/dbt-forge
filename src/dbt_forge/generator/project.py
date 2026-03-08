"""Project file generator — orchestrates directory creation and file rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from dbt_forge.generator.renderer import render_template
from dbt_forge.prompts.questions import ProjectConfig


def generate_project(
    config: ProjectConfig,
    progress_cb: Callable[[str], None] | None = None,
) -> list[Path]:
    """Generate all project files. Returns list of written paths."""
    base = Path(config.output_dir) / config.project_name
    base.mkdir(parents=True, exist_ok=True)

    ctx = _build_context(config)
    written: list[Path] = []

    def write(rel_path: str, content: str) -> None:
        dest = base / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        written.append(dest)
        if progress_cb:
            progress_cb(rel_path)

    def render(template: str) -> str:
        return render_template(template, ctx)

    # Core project files
    write("pyproject.toml", render("pyproject.toml.j2"))
    write(".env", render(".env.j2"))
    write("dbt_project.yml", render("dbt_project.yml.j2"))
    write("packages.yml", render("packages.yml.j2"))
    write(".gitignore", render(".gitignore.j2"))
    write("README.md", render("README.md.j2"))

    # Profile
    adapter_key = config.adapter_key
    write(
        "profiles/profiles.yml",
        render(f"profiles/{adapter_key}.yml.j2"),
    )

    # SQLFluff
    if config.add_sqlfluff:
        write(".sqlfluff", render(".sqlfluff.j2"))

    # GitHub Actions CI
    if config.add_github_actions:
        write(".github/workflows/dbt_ci.yml", render(".github/workflows/dbt_ci.yml.j2"))

    # Empty scaffold directories with README placeholders
    for dirname in ("seeds", "snapshots", "analyses"):
        write(f"{dirname}/.gitkeep", "")

    write("macros/README.md", render("macros/README.md.j2"))

    # Models
    if config.add_examples:
        write(
            "models/staging/example_source/_example_source__sources.yml",
            render("models/staging/example_source/_example_source__sources.yml.j2"),
        )
        write(
            "models/staging/example_source/_example_source__models.yml",
            render("models/staging/example_source/_example_source__models.yml.j2"),
        )
        write(
            "models/staging/example_source/stg_example_source__orders.sql",
            render("models/staging/example_source/stg_example_source__orders.sql.j2"),
        )
        write(
            "tests/assert_positive_total_amount.sql",
            render("tests/assert_positive_total_amount.sql.j2"),
        )

    for mart in config.marts:
        mart_ctx = {**ctx, "mart": mart}
        if config.add_examples:
            write(
                f"models/intermediate/{mart}/int_{mart}__orders_enriched.sql",
                render_template("models/intermediate/int_example.sql.j2", mart_ctx),
            )
            write(
                f"models/marts/{mart}/__{mart}__models.yml",
                render_template("models/marts/__mart__models.yml.j2", mart_ctx),
            )
            write(
                f"models/marts/{mart}/{mart}_orders.sql",
                render_template("models/marts/orders.sql.j2", mart_ctx),
            )
        else:
            write(f"models/intermediate/{mart}/.gitkeep", "")
            write(f"models/marts/{mart}/.gitkeep", "")

    return written


def _build_context(config: ProjectConfig) -> dict:
    return {
        "project_name": config.project_name,
        "adapter": config.adapter,
        "adapter_key": config.adapter_key,
        "dbt_adapter_package": config.dbt_adapter_package,
        "marts": config.marts,
        "packages": config.packages,
        "add_examples": config.add_examples,
        "add_sqlfluff": config.add_sqlfluff,
        "add_github_actions": config.add_github_actions,
    }
