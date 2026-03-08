---
title: Project structure
description: Understand the directories and files created by a dbt-forge scaffold.
---

`dbt-forge` scaffolds a dbt project with a narrow starting structure. The exact files
depend on the options selected during `init`, but the default layout looks like this:

## Generated layout

```text
my_dbt_project/
├── .dbt-forge.yml           # manifest for template updates
├── .env                     # sets DBT_PROFILES_DIR=./profiles
├── .env.example             # optional, adapter-specific env vars
├── .editorconfig            # optional, consistent formatting
├── .gitignore
├── .pre-commit-config.yaml  # optional, pre-commit hooks
├── .sqlfluff                # optional, SQLFluff config
├── .sqlfluffignore          # optional, SQLFluff exclusions
├── CODEOWNERS               # optional, mart-based ownership
├── README.md                # project docs with setup instructions
├── dbt_project.yml
├── packages.yml
├── pyproject.toml           # Python deps (dbt adapter)
├── selectors.yml
├── profiles/
│   └── profiles.yml         # adapter-aware connection config
├── macros/
│   ├── README.md                   # always present
│   ├── generate_schema_name.sql    # optional, dev/prod schema routing
│   └── example_macro.sql           # optional
├── models/
│   ├── intermediate/
│   │   └── <mart>/                 # one subdir per mart
│   ├── marts/
│   │   ├── <mart>/                 # one subdir per mart
│   │   ├── semantic_models/        # optional, MetricFlow
│   │   └── __example__exposures.yml # optional
│   └── staging/
│       └── example_source/         # optional, example models
├── seeds/                  # optional example files
│   ├── example_seed.csv
│   └── _example_seed__seeds.yml
├── snapshots/              # optional example files
│   └── example_snapshot.sql
└── tests/
    ├── assert_positive_total_amount.sql  # optional
    └── unit/                             # optional
        └── test_stg_example.yml
```

## Core files (always generated)

| File | Purpose |
|------|---------|
| `dbt_project.yml` | dbt project configuration (name, version, model paths) |
| `pyproject.toml` | Python project with dbt adapter as a dependency |
| `profiles/profiles.yml` | Adapter-aware connection profile using `env_var()` references |
| `packages.yml` | Selected dbt packages with pinned version ranges |
| `selectors.yml` | dbt selector definitions |
| `.env` | Sets `DBT_PROFILES_DIR=./profiles` for local dbt commands |
| `.gitignore` | Excludes `target/`, `dbt_packages/`, `logs/`, `.env` |
| `README.md` | Project documentation with adapter-specific setup instructions |
| `macros/README.md` | Placeholder for macro documentation |
| `.dbt-forge.yml` | Manifest tracking generated files for `dbt-forge update` |

## Key paths

### `profiles/profiles.yml`

Adapter-aware profile scaffold based on the warehouse selected during `init`. All
sensitive values use `env_var()` so credentials stay out of version control.

### `pyproject.toml`

Python project file listing the dbt adapter as a dependency. Use `uv sync` or
`pip install -e .` to install the project's dependencies.

### `models/staging/`

Source YAML files and starter staging models. With examples enabled, this includes a
sample source (`_example_source__sources.yml`) and staging model (`stg_example_source__records.sql`).

Staging model names follow the convention `stg_<source>__<entity>.sql`.

### `models/intermediate/`

Intermediate models grouped by domain or mart. These are typically ephemeral models
that combine staging models before final mart aggregation.

Intermediate model names follow the convention `int_<mart>__<description>.sql`.

### `models/marts/`

Mart-specific SQL and YAML files, namespaced by the mart you selected during `init` or
added later with `dbt-forge add mart`.

### `tests/`

Data tests and optional dbt unit test examples when that option is enabled.

### `snapshots/`

Present when the snapshot option is enabled during `init`, or after running `dbt-forge add snapshot`.
Contains a `{% snapshot %}` SQL stub configured with the timestamp strategy.

### `seeds/`

Present when the seed option is enabled during `init`, or after running `dbt-forge add seed`.
Contains a CSV stub and a seeds YAML file with column descriptions and tests.

### `macros/example_macro.sql`

Present when the macro option is enabled during `init`, or after running `dbt-forge add macro`.
Contains a named `{% macro %}` block stub.

### `macros/generate_schema_name.sql`

Present when environment config is enabled during `init`. This is the standard dbt macro
override that uses the target schema in dev and the custom schema name in prod. Needed by
virtually every production dbt project.

### `models/marts/__example__exposures.yml`

Present when the exposure option is enabled during `init`, or after running `dbt-forge add exposure`.
Documents a downstream dashboard with `type: dashboard` and an owner block.

### `.env.example`

Present when environment config is enabled during `init`. Contains adapter-specific
environment variable placeholders with comments explaining each one. Copy to `.env`
and fill in your values.

### `.pre-commit-config.yaml`

Present when pre-commit is enabled during `init`, or after running `dbt-forge add pre-commit`.
Configures hooks for trailing whitespace, YAML validation, yamllint, and optionally SQLFluff.

### `.editorconfig`

Present alongside `.pre-commit-config.yaml`. Sets consistent formatting rules: UTF-8 encoding,
LF line endings, 2-space indent for YAML, 4-space indent for SQL and Python.

### `CODEOWNERS`

Present when a team owner is specified during `init`. Maps model directories to team
owners for automatic PR reviewer assignment.

### `.dbt-forge.yml`

Generated by `init` to track the dbt-forge version, project configuration, and SHA-256
hashes of all generated files. Example contents:

```yaml
dbt_forge_version: "0.2.0"
created_at: "2024-01-15T10:30:00"
config:
  project_name: my_dbt_project
  adapter: BigQuery
  marts: ["finance", "marketing"]
  packages: ["dbt-utils", "dbt-expectations"]
  add_examples: true
  add_sqlfluff: true
  # ... remaining config fields
files:
  dbt_project.yml: "a1b2c3d4..."
  profiles/profiles.yml: "e5f6g7h8..."
  # ... SHA-256 hash per generated file
```

Used by [`dbt-forge update`](/docs/cli/update/) to detect which files have changed and
offer to re-apply updated templates. Do not delete this file if you plan to use the
`update` command.

### `.env`

Generated so local dbt commands can resolve `DBT_PROFILES_DIR` consistently. This
tells dbt to look for `profiles.yml` in the `profiles/` directory rather than `~/.dbt/`.

## Naming conventions

The scaffold uses naming prefixes to reduce collisions and make the model layer
obvious at a glance:

| Layer | Prefix | Example |
|-------|--------|---------|
| Staging | `stg_<source>__` | `stg_stripe__payments.sql` |
| Intermediate | `int_<mart>__` | `int_finance__orders_enriched.sql` |
| Marts | (none) | `finance_orders.sql` |

Files prefixed with `_` are YAML schema files, not SQL models:
- `_salesforce__sources.yml` — source definition
- `_salesforce__models.yml` — model YAML entries
- `__example__exposures.yml` — exposure definition

## Structure rules

The generated dbt project follows a few fixed rules:

- Marts are grouped by domain
- Model names are prefixed to reduce naming collisions
- Source files live next to the related staging models
- Optional CI and linting files come from templates instead of manual setup
- Optional components (snapshots, seeds, exposures, macros) are only written when the corresponding prompt is answered yes
- Environment config (`generate_schema_name`, `.env.example`) is generated when enabled
- `CODEOWNERS` maps model directories to the team owner specified during init

The goal is not to cover every possible dbt layout. The scaffold gives you a consistent
starting structure that you can adapt after the project is created.

Use `dbt-forge doctor` to validate that the project continues to follow best practices
as it evolves. Use `dbt-forge update` to re-apply templates when upgrading dbt-forge.
