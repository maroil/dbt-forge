<div align="center">

# dbt-forge

**Scaffold production-ready dbt projects in seconds.**

[![CI](https://github.com/maroil/dbt-forge/actions/workflows/cli-ci.yml/badge.svg)](https://github.com/maroil/dbt-forge/actions/workflows/cli-ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dbt-forge.svg)](https://pypi.org/project/dbt-forge/)
[![Python versions](https://img.shields.io/pypi/pyversions/dbt-forge.svg)](https://pypi.org/project/dbt-forge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/dbt-forge.svg)](https://pypi.org/project/dbt-forge/)

[Installation](#installation) · [Quick Start](#quick-start) · [Commands](#commands) · [Adapters](#supported-adapters) · [Contributing](#contributing)

</div>

---

## Why dbt-forge?

Starting a new dbt project means creating dozens of files, configuring profiles, setting up CI, adding linters, and writing boilerplate YAML. **dbt-forge** does all of this in one command — with interactive prompts or sensible defaults.

- **One command** to scaffold a complete, production-ready dbt project
- **8 database adapters** supported out of the box
- **11 `add` subcommands** to extend projects after init
- **10 health checks** via `doctor` to keep your project clean
- **Team presets** to enforce standards across projects

## Installation

```bash
# With pip
pip install dbt-forge

# With uv (recommended)
uv tool install dbt-forge

# Or run directly without installing
uvx dbt-forge init my_project
```

> **Requirements:** Python 3.11, 3.12, or 3.13

## Quick Start

```bash
# Interactive — choose adapter, marts, packages, CI, and features
dbt-forge init

# Non-interactive — use opinionated defaults
dbt-forge init my_project --defaults

# Preview what would be generated
dbt-forge init my_project --defaults --dry-run

# Use a team preset
dbt-forge init my_project --preset company-standard.yml
```

<details>
<summary><strong>Example generated project structure</strong></summary>

```
my_project/
├── dbt_project.yml
├── packages.yml
├── selectors.yml
├── profiles/
│   └── profiles.yml          # adapter-specific
├── models/
│   ├── staging/
│   │   └── example_source/
│   │       ├── stg_example_source__orders.sql
│   │       ├── _example_source__models.yml
│   │       └── _example_source__sources.yml
│   ├── intermediate/
│   │   └── int_example.sql
│   └── marts/
│       ├── orders.sql
│       └── __mart__models.yml
├── tests/
├── macros/
├── seeds/
├── snapshots/
├── .sqlfluff                 # if enabled
├── .pre-commit-config.yaml   # if enabled
├── .github/workflows/        # if GitHub Actions selected
└── README.md
```

</details>

## Commands

### `init` — Scaffold a new project

```bash
dbt-forge init [PROJECT_NAME] [--defaults] [--dry-run] [--preset FILE] [--output DIR]
```

### `add` — Extend an existing project

Run from inside a dbt project directory:

```bash
# Structural components
dbt-forge add mart finance
dbt-forge add source salesforce
dbt-forge add snapshot orders
dbt-forge add seed dim_country
dbt-forge add exposure weekly_revenue
dbt-forge add macro cents_to_dollars

# Interactive generators
dbt-forge add model users          # prompts for layer, materialization, columns
dbt-forge add test stg_orders      # data, unit, or schema test
dbt-forge add package dbt-utils    # curated registry of 20 packages

# Tooling
dbt-forge add ci github            # also: gitlab, bitbucket
dbt-forge add pre-commit           # hooks + .editorconfig
```

### `doctor` — Health checks

```bash
dbt-forge doctor                       # run all 10 checks
dbt-forge doctor --fix                 # auto-generate missing schema stubs
dbt-forge doctor --ci                  # exit code 1 on failures (for CI)
dbt-forge doctor --check test-coverage # run a single check
```

<details>
<summary><strong>All 10 checks</strong></summary>

| Check | What it verifies |
|---|---|
| `naming-conventions` | Models follow `stg_`, `int_`, mart naming |
| `schema-coverage` | Models are documented in YAML |
| `test-coverage` | Models have at least one test |
| `hardcoded-refs` | No hardcoded `database.schema.table` |
| `packages-pinned` | `packages.yml` has version pins |
| `source-freshness` | Sources have freshness config |
| `orphaned-yml` | No YAML files without corresponding models |
| `sqlfluff-config` | `.sqlfluff` file exists |
| `gitignore` | `.gitignore` is configured |
| `disabled-models` | No disabled models in production |

</details>

### `status` — Project dashboard

```bash
dbt-forge status    # model counts, test/doc coverage, sources, packages
```

### `update` — Re-apply templates

```bash
dbt-forge update --dry-run    # preview changes
dbt-forge update              # interactively accept/skip each file
```

### `preset` — Manage team presets

```bash
dbt-forge preset validate company-standard.yml
```

<details>
<summary><strong>Preset file format</strong></summary>

```yaml
name: "Company Standard"
description: "Enforced dbt project defaults"
defaults:
  adapter: "Snowflake"
  marts: ["finance", "marketing"]
  add_sqlfluff: true
  ci_providers: ["GitHub Actions"]
locked:
  - adapter
  - ci_providers
```

Locked fields cannot be overridden during `init`.

</details>

## Supported Adapters

| Adapter | Profile Template | Package |
|---|---|---|
| BigQuery | `profiles/bigquery.yml` | `dbt-bigquery` |
| Snowflake | `profiles/snowflake.yml` | `dbt-snowflake` |
| PostgreSQL | `profiles/postgresql.yml` | `dbt-postgres` |
| DuckDB | `profiles/duckdb.yml` | `dbt-duckdb` |
| Databricks | `profiles/databricks.yml` | `dbt-databricks` |
| Redshift | `profiles/redshift.yml` | `dbt-redshift` |
| Trino | `profiles/trino.yml` | `dbt-trino` |
| Spark | `profiles/spark.yml` | `dbt-spark` |

## Repository Layout

This is a monorepo:

| Directory | Purpose |
|---|---|
| `cli/` | Python package — published to PyPI |
| `website/` | Docs site — Astro + Starlight (deployed separately) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, test structure, and commit conventions.

```bash
cd cli
uv sync --all-groups
uv run ruff check .
uv run pytest -m "not integration"
```

This project uses [Conventional Commits](https://www.conventionalcommits.org/) — install the hook with:

```bash
uv run pre-commit install --hook-type commit-msg
```

## License

[MIT](LICENSE) © Marouane
