---
title: Project structure
description: Understand the generated layout of a dbt-forge project.
---

## Generated layout

The exact output depends on your answers, but a default scaffold looks like this:

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

## What matters

### `profiles/profiles.yml`

Adapter-specific profile scaffold based on the warehouse selected during `init`.

### `models/staging/`

Source YAML and starter staging models. With examples enabled, this includes a sample `example_source`.

### `models/intermediate/`

Intermediate models grouped by mart or domain.

### `models/marts/`

Mart-specific SQL and YAML files, namespaced by the mart you selected.

### `tests/`

Data tests and optional dbt unit tests when that option is enabled.

### `.env`

Generated so local dbt commands can resolve `DBT_PROFILES_DIR` consistently.

## Why the structure is opinionated

`dbt-forge` optimizes for a fast, repeatable baseline. The generated project is intentionally narrow:

- marts are grouped by domain
- model names are prefixed to avoid collisions
- source files live close to staging models
- optional CI and linting come from templates instead of custom setup
