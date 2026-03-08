---
title: Getting started
description: Install dbt-forge, scaffold a dbt project, and run the first local dbt commands.
---

`dbt-forge` is a Python CLI for scaffolding dbt projects, extending them with new
components, and validating project health. This guide covers the current `0.3.x` alpha.

## Supported Python

- Python 3.11
- Python 3.12
- Python 3.13

## Install

Install `dbt-forge` with either `pip` or `uv`.

```bash
pip install dbt-forge
```

```bash
uv tool install dbt-forge
```

After installing, verify the installation:

```bash
dbt-forge --help
```

## Initialize a dbt project

Run the interactive flow when you want to choose the adapter, starter marts, packages,
and optional setup files:

```bash
dbt-forge init
```

Use defaults when you want a repeatable starting structure without prompts:

```bash
dbt-forge init my_dbt_project --defaults
```

Preview the scaffold without writing files:

```bash
dbt-forge init my_dbt_project --defaults --dry-run
```

Use a preset to enforce team standards:

```bash
dbt-forge init my_dbt_project --preset company-standard.yml
```

See [`init`](/docs/cli/init/) for the full command reference and [`preset`](/docs/cli/preset/)
for the preset file format.

## Default selections

When you use `--defaults`, the CLI selects:

| Setting | Default value |
|---------|---------------|
| Adapter | BigQuery |
| Marts | finance, marketing |
| Packages | dbt-utils, dbt-expectations |
| Example models | yes |
| SQLFluff config | yes |
| CI provider | GitHub Actions |

The following are **disabled** by default and must be enabled interactively or via a preset:

- Unit tests, MetricFlow examples, snapshots, seeds, exposures, macros
- Pre-commit hooks, environment config (`.env.example` + `generate_schema_name`)
- CODEOWNERS file

Treat the defaults as a starting point. Review the generated models, packages, and CI
files before committing them to a team project.

## Inspect the generated project

The exact output depends on the options you choose. A typical scaffold includes:

- `dbt_project.yml` — project configuration
- `pyproject.toml` — Python dependencies (dbt adapter)
- `profiles/profiles.yml` — adapter-aware connection profile
- `packages.yml` — dbt packages with pinned version ranges
- `models/staging/`, `models/intermediate/`, and `models/marts/`
- `tests/`, `macros/`, and `selectors.yml`
- `.dbt-forge.yml` — manifest for template updates (used by `dbt-forge update`)
- optional files: `.sqlfluff`, CI config, `.pre-commit-config.yaml`, `.env.example`, `CODEOWNERS`

Use [Project structure](/docs/project-structure/) for a complete breakdown of every generated file.

## Run the next commands

After the scaffold is written, move into the new dbt project and run the local setup
commands. The generated `.env` file sets `DBT_PROFILES_DIR=./profiles` so dbt can
find the generated `profiles/profiles.yml`:

```bash
cd my_dbt_project
uv sync
uv run --env-file .env dbt deps
uv run --env-file .env dbt debug
```

If you skip starter packages during `init`, `dbt deps` is not required.

## Extend an existing project

Inside an existing dbt project, use the `add` subcommands to scaffold new components
without overwriting files that already exist:

```bash
dbt-forge add mart finance
dbt-forge add source salesforce
dbt-forge add snapshot orders
dbt-forge add seed dim_country
dbt-forge add exposure weekly_revenue
dbt-forge add macro cents_to_dollars
```

Generate models, tests, and CI config interactively:

```bash
dbt-forge add model users           # interactive model generator
dbt-forge add test stg_orders       # data test, unit test, or schema test
dbt-forge add ci github             # CI pipeline config
dbt-forge add pre-commit            # pre-commit hooks + editorconfig
dbt-forge add package dbt-utils     # add a dbt package
```

See [`add`](/docs/cli/add/) for the full command reference.

## Check project health

Run `doctor` from inside a dbt project to validate best practices:

```bash
dbt-forge doctor                    # run all 10 checks
dbt-forge doctor --fix              # auto-generate missing schema stubs
dbt-forge doctor --ci               # non-interactive, exit 1 on failures
dbt-forge doctor --check test-coverage  # run a single check
```

The doctor checks naming conventions, schema/test coverage, hardcoded references,
pinned package versions, source freshness, orphaned YAML entries, and more.
See [`doctor`](/docs/cli/doctor/) for details on each check.

## View project stats

Run `status` for a dashboard overview:

```bash
dbt-forge status
```

Shows model counts by layer (staging, intermediate, marts), test and documentation
coverage percentages, source counts with freshness status, and installed packages.
See [`status`](/docs/cli/status/) for output details.

## Update templates

After upgrading dbt-forge, use `update` to re-apply templates and pick up improvements:

```bash
dbt-forge update --dry-run              # preview what would change
dbt-forge update                        # interactively accept/skip each change
```

The command reads the `.dbt-forge.yml` manifest created during `init`, re-renders
templates with the current version, and shows a diff for each changed file.
See [`update`](/docs/cli/update/) for the full workflow.
