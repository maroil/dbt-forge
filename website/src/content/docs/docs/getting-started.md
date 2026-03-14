---
title: Getting started
description: Install dbt-forge, scaffold a dbt project, and run the first local dbt commands.
---

`dbt-forge` is a Python CLI for scaffolding dbt projects, extending them with new
components, migrating legacy SQL, and validating project health. This guide covers the
current `0.4.x` release.

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

Scaffold a multi-project dbt Mesh setup:

```bash
dbt-forge init my_mesh --mesh
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

Generate sources from live warehouse metadata:

```bash
dbt-forge add source raw_data --from-database
```

Add a sub-project to a dbt Mesh:

```bash
dbt-forge add project analytics
```

See [`add`](/docs/cli/add/) for the full command reference.

## Check project health

Run `doctor` from inside a dbt project to validate best practices:

```bash
dbt-forge doctor                    # run all 11 checks
dbt-forge doctor --fix              # auto-fix schema stubs + contract config
dbt-forge doctor --ci               # non-interactive, exit 1 on failures
dbt-forge doctor --check test-coverage  # run a single check
dbt-forge doctor --format json      # machine-readable output
```

The doctor checks naming conventions, schema/test coverage, hardcoded references,
pinned package versions, source freshness, orphaned YAML entries, contract
enforcement, and more. Each failing check includes a specific remediation hint.
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

## Migrate legacy SQL

Convert a directory of SQL scripts into a dbt project:

```bash
dbt-forge migrate ./legacy_sql/
dbt-forge migrate ./legacy_sql/ --dry-run   # preview without writing
```

The command parses `CREATE TABLE/VIEW` statements, builds a dependency graph, and
generates dbt models with `ref()` and `source()` replacing raw table references. Each
model is assigned to staging, intermediate, or marts based on its dependencies. A
migration report summarizes the results.

See [`migrate`](/docs/cli/migrate/) for the full command reference.

## Lint project structure

Run `lint` to check for architectural issues that SQL linters miss:

```bash
dbt-forge lint                         # run all 6 rules
dbt-forge lint --rule fan-out          # single rule
dbt-forge lint --ci                    # exit 1 on warnings
dbt-forge lint --format json           # machine-readable output
```

The lint rules check DAG fan-out, source-to-mart violations, model complexity,
duplicate logic, circular dependencies, and YAML-SQL column drift. Customize
thresholds with a `.dbt-forge-lint.yml` file.

See [`lint`](/docs/cli/lint/) for the full command reference.

## Analyze change impact

Run `impact` to see which downstream models are affected by a change:

```bash
dbt-forge impact stg_orders            # downstream tree for one model
dbt-forge impact --diff                # detect changes from git diff
dbt-forge impact --diff --pr           # markdown for PR descriptions
dbt-forge impact --format json         # machine-readable output
```

See [`impact`](/docs/cli/impact/) for output examples and options.

## Estimate query costs

Run `cost` to identify expensive models from warehouse usage data:

```bash
dbt-forge cost                         # top 10 models, last 30 days
dbt-forge cost --days 7 --top 20       # custom range
dbt-forge cost --report                # markdown report
dbt-forge cost --format json           # machine-readable output
```

Supports BigQuery, Snowflake, and Databricks. Includes materialization suggestions.

See [`cost`](/docs/cli/cost/) for supported warehouses and output details.

## Generate data contracts

Run `contracts generate` to create dbt data contracts from warehouse column types:

```bash
dbt-forge contracts generate orders           # single model
dbt-forge contracts generate --all-public     # all public models
dbt-forge contracts generate --dry-run        # preview
```

Adds `contract: { enforced: true }`, `data_type`, and `not_null` tests. Preserves
existing descriptions and tests.

See [`contracts`](/docs/cli/contracts/) for the full command reference.

## Track model changes

Run `changelog generate` to detect breaking schema changes between git refs:

```bash
dbt-forge changelog generate                          # latest tag to HEAD
dbt-forge changelog generate --from v1.0 --to v2.0
dbt-forge changelog generate --format json            # machine-readable
dbt-forge changelog generate --breaking-only          # breaking only
```

See [`changelog`](/docs/cli/changelog/) for change classification details.

## Generate documentation with AI

Generate model and column descriptions using an LLM:

```bash
dbt-forge docs generate                      # all undocumented models
dbt-forge docs generate --model stg_orders   # single model
dbt-forge docs generate --provider ollama    # use local Ollama
```

Supports Claude (Anthropic), OpenAI, and Ollama. The command reads model SQL, sends it
to the LLM, and presents generated descriptions for interactive review before updating
YAML files. Existing descriptions are preserved.

See [`docs generate`](/docs/cli/docs/) for the full command reference.
