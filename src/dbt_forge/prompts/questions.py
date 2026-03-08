"""Interactive prompts for dbt-forge init."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

import questionary
from rich.console import Console

console = Console()

ADAPTERS = [
    "BigQuery",
    "Snowflake",
    "PostgreSQL",
    "DuckDB",
    "Databricks",
    "Redshift",
    "Trino",
    "Spark",
]

MARTS = ["finance", "marketing", "operations", "product", "engineering"]

PACKAGES = [
    ("dbt-utils", "utility macros & tests"),
    ("dbt-expectations", "data quality tests"),
    ("dbt-codegen", "auto-generate YAML"),
    ("elementary-data", "observability & alerts"),
]

PACKAGE_CHOICES = [
    questionary.Choice(
        title=f"{name}  ({desc})",
        value=name,
        checked=(name in {"dbt-utils", "dbt-expectations"}),
    )
    for name, desc in PACKAGES
]

CI_PROVIDERS = ["GitHub Actions", "GitLab CI", "Bitbucket Pipelines"]

CI_PROVIDER_CHOICES = [
    questionary.Choice(
        title=provider,
        value=provider,
        checked=(provider == "GitHub Actions"),
    )
    for provider in CI_PROVIDERS
]


@dataclass
class ProjectConfig:
    project_name: str
    adapter: str
    marts: list[str]
    packages: list[str]
    add_examples: bool
    add_sqlfluff: bool
    ci_providers: list[str] = field(default_factory=list)
    add_unit_tests: bool = False
    add_metricflow: bool = False
    output_dir: str = "."

    @property
    def adapter_key(self) -> str:
        return self.adapter.lower().replace(" ", "_").replace("/", "_")

    @property
    def dbt_adapter_package(self) -> str:
        mapping = {
            "BigQuery": "dbt-bigquery",
            "Snowflake": "dbt-snowflake",
            "PostgreSQL": "dbt-postgres",
            "DuckDB": "dbt-duckdb",
            "Databricks": "dbt-databricks",
            "Redshift": "dbt-redshift",
            "Trino": "dbt-trino",
            "Spark": "dbt-spark",
        }
        return mapping.get(self.adapter, "dbt-core")

    @property
    def add_github_actions(self) -> bool:
        return "GitHub Actions" in self.ci_providers

    @property
    def add_gitlab_ci(self) -> bool:
        return "GitLab CI" in self.ci_providers

    @property
    def add_bitbucket_pipelines(self) -> bool:
        return "Bitbucket Pipelines" in self.ci_providers


def _slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def _validate_project_name(value: str) -> bool | str:
    if not value.strip():
        return "Project name cannot be empty."
    slug = _slugify(value)
    if not re.match(r"^[a-z][a-z0-9_]*$", slug):
        return (
            "Project name must start with a letter and contain only letters, "
            "numbers, or underscores."
        )
    return True


def gather_config(
    project_name: str | None,
    use_defaults: bool,
    output_dir: str,
) -> ProjectConfig:
    """Run interactive prompts and return a ProjectConfig."""

    if use_defaults:
        name = project_name or "my_dbt_project"
        return ProjectConfig(
            project_name=_slugify(name),
            adapter="BigQuery",
            marts=["finance", "marketing"],
            packages=["dbt-utils", "dbt-expectations"],
            add_examples=True,
            add_sqlfluff=True,
            ci_providers=["GitHub Actions"],
            add_unit_tests=False,
            add_metricflow=False,
            output_dir=output_dir,
        )

    # --- Project name ---
    if project_name:
        name = _slugify(project_name)
    else:
        answer = questionary.text(
            "Project name:",
            validate=_validate_project_name,
            style=_style(),
        ).ask()
        if answer is None:
            _abort()
        name = _slugify(answer)

    # --- Adapter ---
    adapter = questionary.select(
        "Warehouse adapter:",
        choices=ADAPTERS,
        style=_style(),
    ).ask()
    if adapter is None:
        _abort()

    # --- Marts ---
    mart_choices = [
        questionary.Choice(title=m, value=m, checked=(m in {"finance", "marketing"}))
        for m in MARTS
    ]
    marts = questionary.checkbox(
        "Which marts/departments to scaffold? (space to select)",
        choices=mart_choices,
        style=_style(),
        validate=lambda v: True if v else "Select at least one mart.",
    ).ask()
    if marts is None:
        _abort()

    # --- Packages ---
    packages = questionary.checkbox(
        "Include packages? (space to select)",
        choices=PACKAGE_CHOICES,
        style=_style(),
    ).ask()
    if packages is None:
        _abort()

    # --- Optional extras ---
    add_examples = questionary.confirm(
        "Add example models and tests?",
        default=True,
        style=_style(),
    ).ask()
    if add_examples is None:
        _abort()

    add_sqlfluff = questionary.confirm(
        "Add SQLFluff config?",
        default=True,
        style=_style(),
    ).ask()
    if add_sqlfluff is None:
        _abort()

    # --- CI providers (multi-select) ---
    ci_providers = questionary.checkbox(
        "Add CI/CD config? (space to select, none = skip)",
        choices=CI_PROVIDER_CHOICES,
        style=_style(),
    ).ask()
    if ci_providers is None:
        _abort()

    # --- dbt unit tests (dbt 1.8+) ---
    add_unit_tests = False
    if add_examples:
        add_unit_tests = questionary.confirm(
            "Add dbt unit test examples? (dbt 1.8+)",
            default=False,
            style=_style(),
        ).ask()
        if add_unit_tests is None:
            _abort()

    # --- MetricFlow / Semantic Layer (dbt 1.6+) ---
    add_metricflow = questionary.confirm(
        "Add MetricFlow semantic model examples? (dbt 1.6+)",
        default=False,
        style=_style(),
    ).ask()
    if add_metricflow is None:
        _abort()

    return ProjectConfig(
        project_name=name,
        adapter=adapter,
        marts=marts,
        packages=packages,
        add_examples=add_examples,
        add_sqlfluff=add_sqlfluff,
        ci_providers=ci_providers,
        add_unit_tests=add_unit_tests,
        add_metricflow=add_metricflow,
        output_dir=output_dir,
    )


def _style() -> questionary.Style:
    return questionary.Style(
        [
            ("qmark", "fg:#00d7ff bold"),
            ("question", "bold"),
            ("answer", "fg:#00d7ff bold"),
            ("pointer", "fg:#00d7ff bold"),
            ("highlighted", "fg:#00d7ff bold"),
            ("selected", "fg:#00d7ff"),
            ("separator", "fg:#6c6c6c"),
            ("instruction", "fg:#6c6c6c"),
        ]
    )


def _abort() -> None:
    console.print("\n[dim]Aborted.[/dim]")
    sys.exit(0)
