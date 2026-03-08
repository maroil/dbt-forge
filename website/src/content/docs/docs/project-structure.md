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
├── .gitignore
├── dbt_project.yml
├── packages.yml
├── pyproject.toml
├── profiles/
│   └── profiles.yml
├── macros/
│   └── README.md           # always present
│   └── example_macro.sql   # optional
├── models/
│   ├── intermediate/
│   ├── marts/
│   └── staging/
├── seeds/                  # optional example files
├── snapshots/              # optional example files
├── selectors.yml
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

### `models/marts/__example__exposures.yml`

Present when the exposure option is enabled during `init`, or after running `dbt-forge add exposure`.
Documents a downstream dashboard with `type: dashboard` and an owner block.

### `.env`

Generated so local dbt commands can resolve `DBT_PROFILES_DIR` consistently.

## Structure rules

The generated dbt project follows a few fixed rules:

- marts are grouped by domain
- model names are prefixed to reduce naming collisions
- source files live next to the related staging models
- optional CI and linting files come from templates instead of manual setup
- optional components (snapshots, seeds, exposures, macros) are only written when the corresponding prompt is answered yes

The goal is not to cover every possible dbt layout. The scaffold gives you a consistent
starting structure that you can adapt after the project is created.
