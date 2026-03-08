"""Project file generator — orchestrates directory creation and file rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from dbt_forge.generator.renderer import render_template
from dbt_forge.prompts.questions import ProjectConfig


def generate_project(
    config: ProjectConfig,
    progress_cb: Callable[[str], None] | None = None,
    dry_run: bool = False,
) -> list[Path]:
    """Generate all project files. Returns list of written (or would-be-written) paths.

    When *dry_run* is True no files are created; the returned list still contains
    all paths that *would* have been written so callers can display a preview tree.
    """
    base = Path(config.output_dir) / config.project_name

    if not dry_run:
        base.mkdir(parents=True, exist_ok=True)

    ctx = _build_context(config)
    written: list[Path] = []

    def write(rel_path: str, content: str) -> None:
        dest = base / rel_path
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        written.append(dest)
        if progress_cb:
            progress_cb(rel_path)

    def render(template: str) -> str:
        if dry_run:
            return ""
        return render_template(template, ctx)

    def render_ctx(template: str, extra_ctx: dict) -> str:
        if dry_run:
            return ""
        return render_template(template, extra_ctx)

    # Core project files
    write("pyproject.toml", render("pyproject.toml.j2"))
    write(".env", render(".env.j2"))
    write("dbt_project.yml", render("dbt_project.yml.j2"))
    write("packages.yml", render("packages.yml.j2"))
    write(".gitignore", render(".gitignore.j2"))
    write("README.md", render("README.md.j2"))
    write("selectors.yml", render("selectors.yml.j2"))

    # Profile
    adapter_key = config.adapter_key
    write(
        "profiles/profiles.yml",
        render(f"profiles/{adapter_key}.yml.j2"),
    )

    # SQLFluff
    if config.add_sqlfluff:
        write(".sqlfluff", render(".sqlfluff.j2"))

    # CI providers
    if config.add_github_actions:
        write(".github/workflows/dbt_ci.yml", render(".github/workflows/dbt_ci.yml.j2"))
    if config.add_gitlab_ci:
        write(".gitlab-ci.yml", render(".gitlab-ci.yml.j2"))
    if config.add_bitbucket_pipelines:
        write("bitbucket-pipelines.yml", render("bitbucket-pipelines.yml.j2"))

    # Empty scaffold directories with README placeholders
    for dirname in ("analyses",):
        write(f"{dirname}/.gitkeep", "")
    if not config.add_seed:
        write("seeds/.gitkeep", "")
    if not config.add_snapshot:
        write("snapshots/.gitkeep", "")

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

        # Unit tests (dbt 1.8+)
        if config.add_unit_tests:
            write(
                "tests/unit/test_stg_example.yml",
                render("tests/unit/test_stg_example.yml.j2"),
            )

    for mart in config.marts:
        mart_ctx = {**ctx, "mart": mart}
        if config.add_examples:
            write(
                f"models/intermediate/{mart}/int_{mart}__orders_enriched.sql",
                render_ctx("models/intermediate/int_example.sql.j2", mart_ctx),
            )
            write(
                f"models/marts/{mart}/__{mart}__models.yml",
                render_ctx("models/marts/__mart__models.yml.j2", mart_ctx),
            )
            write(
                f"models/marts/{mart}/{mart}_orders.sql",
                render_ctx("models/marts/orders.sql.j2", mart_ctx),
            )
        else:
            write(f"models/intermediate/{mart}/.gitkeep", "")
            write(f"models/marts/{mart}/.gitkeep", "")

    # MetricFlow / Semantic Layer (dbt 1.6+)
    if config.add_metricflow:
        write(
            "models/marts/semantic_models/sem_orders.yml",
            render("models/marts/semantic_models/sem_orders.yml.j2"),
        )

    # Snapshot example
    if config.add_snapshot:
        write(
            "snapshots/example_snapshot.sql",
            render("snapshots/example_snapshot.sql.j2"),
        )

    # Seed example
    if config.add_seed:
        write("seeds/example_seed.csv", render("seeds/example_seed.csv.j2"))
        write(
            "seeds/_example_seed__seeds.yml",
            render("seeds/_example_seed__seeds.yml.j2"),
        )

    # Exposure example
    if config.add_exposure:
        write(
            "models/marts/__example__exposures.yml",
            render("models/marts/__example__exposures.yml.j2"),
        )

    # Macro example
    if config.add_macro:
        write("macros/example_macro.sql", render("macros/example_macro.sql.j2"))

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
        "ci_providers": config.ci_providers,
        "add_github_actions": config.add_github_actions,
        "add_gitlab_ci": config.add_gitlab_ci,
        "add_bitbucket_pipelines": config.add_bitbucket_pipelines,
        "add_unit_tests": config.add_unit_tests,
        "add_metricflow": config.add_metricflow,
        "add_snapshot": config.add_snapshot,
        "add_seed": config.add_seed,
        "add_exposure": config.add_exposure,
        "add_macro": config.add_macro,
    }
