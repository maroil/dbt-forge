---
title: init
description: Command reference for scaffolding a new dbt project with dbt-forge.
---

`dbt-forge init` scaffolds a new dbt project. Use it when you want a consistent
starting structure instead of building folders and setup files by hand.

## Command

```bash
dbt-forge init [PROJECT_NAME] [--defaults] [--output PATH] [--dry-run] [--preset PATH]
```

## What it does

The command:

- collects configuration through interactive prompts or `--defaults`
- scaffolds a dbt project directory with core files and optional setup files
- writes a `.dbt-forge.yml` manifest to track generated files for future updates
- prints the next local commands to run after the scaffold is written

## Arguments

### `PROJECT_NAME`

Optional project name for the generated dbt project.

- When omitted in interactive mode, the CLI prompts for it.
- Names are slugified to lowercase with underscores (e.g., `My Project` becomes `my_project`).

## Options

### `--defaults`, `-d`

Skip interactive prompts and use the default configuration:

| Setting | Default value |
|---------|---------------|
| Adapter | BigQuery |
| Marts | finance, marketing |
| Packages | dbt-utils, dbt-expectations |
| Example models | yes |
| SQLFluff config | yes |
| CI provider | GitHub Actions |
| Unit tests | no |
| MetricFlow | no |
| Snapshot | no |
| Seed | no |
| Exposure | no |
| Macro | no |
| Pre-commit | no |
| Env config | no |
| CODEOWNERS | no |

### `--output`, `-o`

Choose the directory where the project folder should be created.

```bash
dbt-forge init analytics_core --defaults --output ./sandbox
```

### `--dry-run`

Show the files that would be written without creating anything on disk. Renders a tree
view of the full project structure.

### `--preset`, `-p`

Apply a preset YAML file to pre-fill or lock prompt selections. Accepts a local file
path or HTTPS URL.

```bash
dbt-forge init my_project --preset company-standard.yml
dbt-forge init my_project --preset https://example.com/presets/standard.yml
```

The preset is validated before prompts begin. If validation fails, `init` exits without
scaffolding. See [preset](/docs/cli/preset/) for the file format.

When combined with `--defaults`, preset values are applied but no prompts are shown.
When used interactively, locked fields are skipped and default fields pre-populate
the prompt selections.

## Interactive prompts

Without `--defaults`, `init` asks for the following in order:

| Prompt | Field | Generated files |
|--------|-------|-----------------|
| Project name | `project_name` | Used as the directory name and in `dbt_project.yml` |
| Warehouse adapter | `adapter` | `profiles/profiles.yml` with adapter-specific config |
| Marts to scaffold | `marts` | `models/marts/<name>/` and `models/intermediate/<name>/` per mart |
| Starter packages | `packages` | Entries in `packages.yml` |
| Example models and tests | `add_examples` | `models/staging/example_source/`, `tests/assert_positive_total_amount.sql`, mart SQL/YAML |
| SQLFluff config | `add_sqlfluff` | `.sqlfluff`, `.sqlfluffignore` |
| CI providers | `ci_providers` | `.github/workflows/dbt_ci.yml`, `.gitlab-ci.yml`, or `bitbucket-pipelines.yml` |
| Unit test examples | `add_unit_tests` | `tests/unit/test_stg_example.yml` (only if examples enabled) |
| MetricFlow examples | `add_metricflow` | `models/marts/semantic_models/sem_orders.yml` |
| Example snapshot | `add_snapshot` | `snapshots/example_snapshot.sql` |
| Example seed | `add_seed` | `seeds/example_seed.csv`, `seeds/_example_seed__seeds.yml` |
| Example exposure | `add_exposure` | `models/marts/__example__exposures.yml` |
| Example macro | `add_macro` | `macros/example_macro.sql` |
| Pre-commit hooks | `add_pre_commit` | `.pre-commit-config.yaml`, `.editorconfig` |
| Environment config | `add_env_config` | `.env.example`, `macros/generate_schema_name.sql` |
| Team owner | `team_owner` | `CODEOWNERS` with mart-based ownership mapping |

## Generated output

Every scaffold includes these core files:

- `dbt_project.yml` — project configuration
- `pyproject.toml` — Python dependencies (dbt adapter)
- `profiles/profiles.yml` — adapter-aware connection profile using `env_var()`
- `packages.yml` — selected dbt packages with pinned version ranges
- `selectors.yml` — dbt selector definitions
- `.env` — sets `DBT_PROFILES_DIR=./profiles` for local dbt commands
- `.gitignore` — excludes `target/`, `dbt_packages/`, `logs/`, `.env`
- `README.md` — project documentation with adapter-specific setup instructions
- `macros/README.md` — placeholder for macro documentation
- `.dbt-forge.yml` — manifest tracking generated files (used by [`dbt-forge update`](/docs/cli/update/))

Optional files depend on the prompts answered:

| Feature | Files generated |
|---------|----------------|
| SQLFluff | `.sqlfluff`, `.sqlfluffignore` |
| Pre-commit | `.pre-commit-config.yaml`, `.editorconfig` |
| CI — GitHub Actions | `.github/workflows/dbt_ci.yml` |
| CI — GitLab CI | `.gitlab-ci.yml` |
| CI — Bitbucket Pipelines | `bitbucket-pipelines.yml` |
| Environment config | `.env.example`, `macros/generate_schema_name.sql` |
| CODEOWNERS | `CODEOWNERS` |
| Examples | `models/staging/example_source/` (3 files), `tests/assert_positive_total_amount.sql` |
| Examples + mart | `models/marts/<mart>/<mart>_orders.sql`, `models/marts/<mart>/__<mart>__models.yml`, `models/intermediate/<mart>/int_<mart>__orders_enriched.sql` |
| Unit tests | `tests/unit/test_stg_example.yml` |
| MetricFlow | `models/marts/semantic_models/sem_orders.yml` |
| Snapshot | `snapshots/example_snapshot.sql` |
| Seed | `seeds/example_seed.csv`, `seeds/_example_seed__seeds.yml` |
| Exposure | `models/marts/__example__exposures.yml` |
| Macro | `macros/example_macro.sql` |

## Supported adapters

BigQuery, Snowflake, PostgreSQL, DuckDB, Databricks, Redshift, Trino, Spark.

Each adapter generates a different `profiles/profiles.yml` with the correct connection
fields and `env_var()` references.

## Behavior and limits

- `--dry-run` resolves the full config and project path but does not write files or create the manifest.
- The command always prints a banner and next-step hints for the generated project.
- If the project directory already exists, files are written into it without deleting existing content.
- Run `dbt-forge --help` for a quick overview of all available commands.
