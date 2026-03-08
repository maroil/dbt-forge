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
│   └── README.md
├── models/
│   ├── intermediate/
│   ├── marts/
│   └── staging/
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

### `.env`

Generated so local dbt commands can resolve `DBT_PROFILES_DIR` consistently.

## Structure rules

The generated dbt project follows a few fixed rules:

- marts are grouped by domain
- model names are prefixed to reduce naming collisions
- source files live next to the related staging models
- optional CI and linting files come from templates instead of manual setup

The goal is not to cover every possible dbt layout. The scaffold gives you a consistent
starting structure that you can adapt after the project is created.
