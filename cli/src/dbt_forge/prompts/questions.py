"""Interactive prompts for dbt-forge init."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import questionary
from rich.console import Console

if TYPE_CHECKING:
    from dbt_forge.mesh import MeshProjectConfig

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
    add_snapshot: bool = False
    add_seed: bool = False
    add_exposure: bool = False
    add_macro: bool = False
    add_pre_commit: bool = False
    add_env_config: bool = False
    team_owner: str = ""
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
    preset: object | None = None,
) -> ProjectConfig:
    """Run interactive prompts and return a ProjectConfig.

    If *preset* is provided (a PresetConfig), locked fields are skipped and
    default fields override questionary defaults.
    """
    # Helper to check preset
    def _is_locked(field: str) -> bool:
        return preset is not None and field in getattr(preset, "locked", [])

    def _preset_default(field: str, fallback):
        if preset is not None:
            return getattr(preset, "defaults", {}).get(field, fallback)
        return fallback

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
    if _is_locked("adapter"):
        adapter = _preset_default("adapter", "BigQuery")
    else:
        default_adapter = _preset_default("adapter", None)
        adapter = questionary.select(
            "Warehouse adapter:",
            choices=ADAPTERS,
            default=default_adapter if default_adapter in ADAPTERS else None,
            style=_style(),
        ).ask()
        if adapter is None:
            _abort()

    # --- Marts ---
    if _is_locked("marts"):
        marts = _preset_default("marts", ["finance", "marketing"])
    else:
        preset_marts = _preset_default("marts", None)
        default_marts = set(preset_marts) if preset_marts else {"finance", "marketing"}
        mart_choices = [
            questionary.Choice(title=m, value=m, checked=(m in default_marts))
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

    if _is_locked("add_sqlfluff"):
        add_sqlfluff = _preset_default("add_sqlfluff", True)
    else:
        add_sqlfluff = questionary.confirm(
            "Add SQLFluff config?",
            default=_preset_default("add_sqlfluff", True),
            style=_style(),
        ).ask()
        if add_sqlfluff is None:
            _abort()

    # --- CI providers (multi-select) ---
    if _is_locked("ci_providers"):
        ci_providers = _preset_default("ci_providers", [])
    else:
        preset_ci = _preset_default("ci_providers", None)
        default_ci = set(preset_ci) if preset_ci else {"GitHub Actions"}
        ci_choices = [
            questionary.Choice(
                title=provider,
                value=provider,
                checked=(provider in default_ci),
            )
            for provider in CI_PROVIDERS
        ]
        ci_providers = questionary.checkbox(
            "Add CI/CD config? (space to select, none = skip)",
            choices=ci_choices,
            style=_style(),
        ).ask()
        if ci_providers is None:
            _abort()

    # --- dbt unit tests (dbt 1.8+) ---
    add_unit_tests = False
    if add_examples:
        if _is_locked("add_unit_tests"):
            add_unit_tests = _preset_default("add_unit_tests", False)
        else:
            add_unit_tests = questionary.confirm(
                "Add dbt unit test examples? (dbt 1.8+)",
                default=_preset_default("add_unit_tests", False),
                style=_style(),
            ).ask()
            if add_unit_tests is None:
                _abort()

    # --- MetricFlow / Semantic Layer (dbt 1.6+) ---
    if _is_locked("add_metricflow"):
        add_metricflow = _preset_default("add_metricflow", False)
    else:
        add_metricflow = questionary.confirm(
            "Add MetricFlow semantic model examples? (dbt 1.6+)",
            default=_preset_default("add_metricflow", False),
            style=_style(),
        ).ask()
        if add_metricflow is None:
            _abort()

    # --- Snapshots ---
    if _is_locked("add_snapshot"):
        add_snapshot = _preset_default("add_snapshot", False)
    else:
        add_snapshot = questionary.confirm(
            "Add an example snapshot?",
            default=_preset_default("add_snapshot", False),
            style=_style(),
        ).ask()
        if add_snapshot is None:
            _abort()

    # --- Seeds ---
    if _is_locked("add_seed"):
        add_seed = _preset_default("add_seed", False)
    else:
        add_seed = questionary.confirm(
            "Add an example seed (CSV reference data)?",
            default=_preset_default("add_seed", False),
            style=_style(),
        ).ask()
        if add_seed is None:
            _abort()

    # --- Exposures ---
    if _is_locked("add_exposure"):
        add_exposure = _preset_default("add_exposure", False)
    else:
        add_exposure = questionary.confirm(
            "Add an example exposure (downstream dashboard)?",
            default=_preset_default("add_exposure", False),
            style=_style(),
        ).ask()
        if add_exposure is None:
            _abort()

    # --- Macros ---
    if _is_locked("add_macro"):
        add_macro = _preset_default("add_macro", False)
    else:
        add_macro = questionary.confirm(
            "Add an example macro?",
            default=_preset_default("add_macro", False),
            style=_style(),
        ).ask()
        if add_macro is None:
            _abort()

    # --- Pre-commit hooks ---
    if _is_locked("add_pre_commit"):
        add_pre_commit = _preset_default("add_pre_commit", False)
    else:
        add_pre_commit = questionary.confirm(
            "Add pre-commit hooks config? (SQLFluff, yamllint, etc.)",
            default=_preset_default("add_pre_commit", add_sqlfluff),
            style=_style(),
        ).ask()
        if add_pre_commit is None:
            _abort()

    # --- Environment config (generate_schema_name + .env.example) ---
    if _is_locked("add_env_config"):
        add_env_config = _preset_default("add_env_config", True)
    else:
        add_env_config = questionary.confirm(
            "Add environment config? (generate_schema_name macro + .env.example)",
            default=_preset_default("add_env_config", True),
            style=_style(),
        ).ask()
        if add_env_config is None:
            _abort()

    # --- CODEOWNERS ---
    if _is_locked("team_owner"):
        team_owner = _preset_default("team_owner", "")
    else:
        team_owner = questionary.text(
            "Team owner for CODEOWNERS (e.g. @my-org/data-team, leave blank to skip):",
            default=_preset_default("team_owner", ""),
            style=_style(),
        ).ask()
        if team_owner is None:
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
        add_snapshot=add_snapshot,
        add_seed=add_seed,
        add_exposure=add_exposure,
        add_macro=add_macro,
        add_pre_commit=add_pre_commit,
        add_env_config=add_env_config,
        team_owner=team_owner.strip(),
        output_dir=output_dir,
    )


def gather_mesh_config(
    project_name: str | None = None,
    output_dir: str = ".",
) -> MeshProjectConfig:
    """Interactive prompts for mesh project configuration."""
    from dbt_forge.mesh import MeshProjectConfig, SubProjectConfig

    # Project name
    if project_name:
        name = _slugify(project_name)
    else:
        answer = questionary.text(
            "Mesh project name:",
            validate=_validate_project_name,
            style=_style(),
        ).ask()
        if answer is None:
            _abort()
        name = _slugify(answer)

    # Adapter
    adapter = questionary.select(
        "Warehouse adapter:",
        choices=ADAPTERS,
        style=_style(),
    ).ask()
    if adapter is None:
        _abort()

    adapter_key = adapter.lower().replace(" ", "_").replace("/", "_")
    adapter_pkg_map = {
        "BigQuery": "dbt-bigquery",
        "Snowflake": "dbt-snowflake",
        "PostgreSQL": "dbt-postgres",
        "DuckDB": "dbt-duckdb",
        "Databricks": "dbt-databricks",
        "Redshift": "dbt-redshift",
        "Trino": "dbt-trino",
        "Spark": "dbt-spark",
    }
    dbt_adapter_package = adapter_pkg_map.get(adapter, "dbt-core")

    # Preset or custom
    setup_style = questionary.select(
        "Sub-project setup:",
        choices=[
            questionary.Choice(
                "Preset: staging \u2192 transform \u2192 marts", value="preset"
            ),
            questionary.Choice(
                "Custom: define sub-projects manually", value="custom"
            ),
        ],
        style=_style(),
    ).ask()
    if setup_style is None:
        _abort()

    sub_projects: list[SubProjectConfig] = []
    if setup_style == "preset":
        sub_projects = [
            SubProjectConfig(name="staging", purpose="staging"),
            SubProjectConfig(
                name="transform", purpose="intermediate", upstream_deps=["staging"]
            ),
            SubProjectConfig(
                name="marts", purpose="marts", upstream_deps=["transform"]
            ),
        ]
    else:
        while True:
            sp_name = questionary.text(
                "Sub-project name (blank to finish):",
                style=_style(),
            ).ask()
            if sp_name is None:
                _abort()
            if not sp_name.strip():
                if not sub_projects:
                    console.print("[red]At least one sub-project is required.[/red]")
                    continue
                break

            sp_purpose = questionary.text(
                f"Purpose for '{sp_name}' (e.g. staging, transform, marts):",
                default="",
                style=_style(),
            ).ask()
            if sp_purpose is None:
                _abort()

            upstream: list[str] = []
            if sub_projects:
                existing_names = [sp.name for sp in sub_projects]
                selected_deps = questionary.checkbox(
                    f"Upstream dependencies for '{sp_name}':",
                    choices=[
                        questionary.Choice(n, value=n) for n in existing_names
                    ],
                    style=_style(),
                ).ask()
                if selected_deps is None:
                    _abort()
                upstream = selected_deps

            sub_projects.append(
                SubProjectConfig(
                    name=_slugify(sp_name),
                    purpose=sp_purpose,
                    upstream_deps=upstream,
                )
            )

    return MeshProjectConfig(
        name=name,
        adapter=adapter,
        adapter_key=adapter_key,
        dbt_adapter_package=dbt_adapter_package,
        sub_projects=sub_projects,
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
