---
title: Project structure
description: Understand the directories and files created by a dbt-forge scaffold.
---

`dbt-forge` scaffolds a dbt project with a narrow starting structure. The exact files
depend on the options selected during `init`, but the default layout looks like this:

## Generated layout

```text
my_dbt_project/
├── .env
├── .env.example             # optional, adapter-specific env vars
├── .editorconfig            # optional, consistent formatting
├── .gitignore
├── .pre-commit-config.yaml  # optional, pre-commit hooks
├── .sqlfluff                # optional, SQLFluff config
├── .sqlfluffignore          # optional, SQLFluff exclusions
├── CODEOWNERS               # optional, mart-based ownership
├── dbt_project.yml
├── packages.yml
├── pyproject.toml
├── selectors.yml
├── profiles/
│   └── profiles.yml
├── macros/
│   ├── README.md                   # always present
│   ├── generate_schema_name.sql    # optional, dev/prod schema routing
│   └── example_macro.sql           # optional
├── models/
│   ├── intermediate/
│   ├── marts/
│   └── staging/
├── seeds/                  # optional example files
├── snapshots/              # optional example files
└── tests/
```

## Key paths

### `profiles/profiles.yml`

Adapter-aware profile scaffold based on the warehouse selected during `init`.

### `models/staging/`

Source YAML files and starter staging models. With examples enabled, this includes a
sample source and staging model.

### `models/intermediate/`

Intermediate models grouped by domain or mart.

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

### `.env`

Generated so local dbt commands can resolve `DBT_PROFILES_DIR` consistently.

## Structure rules

The generated dbt project follows a few fixed rules:

- marts are grouped by domain
- model names are prefixed to reduce naming collisions
- source files live next to the related staging models
- optional CI and linting files come from templates instead of manual setup
- optional components (snapshots, seeds, exposures, macros) are only written when the corresponding prompt is answered yes
- environment config (`generate_schema_name`, `.env.example`) is generated when enabled
- `CODEOWNERS` maps model directories to the team owner specified during init

The goal is not to cover every possible dbt layout. The scaffold gives you a consistent
starting structure that you can adapt after the project is created.

Use `dbt-forge doctor` to validate that the project continues to follow best practices
as it evolves.
