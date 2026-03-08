---
title: add
description: Reference for the dbt-forge add subcommands.
---

## Synopsis

```bash
dbt-forge add mart NAME
dbt-forge add source NAME
```

## Project detection

The `add` commands must run from inside an existing dbt project. The CLI walks upward from the current directory until it finds `dbt_project.yml`.

If no dbt project is found, the command exits with an error.

## `add mart`

```bash
dbt-forge add mart finance
```

This scaffolds:

- `models/marts/<name>/<name>_orders.sql`
- `models/marts/<name>/__<name>__models.yml`
- `models/intermediate/<name>/int_<name>__orders_enriched.sql`

The command does not overwrite files that already exist.

## `add source`

```bash
dbt-forge add source salesforce
```

This scaffolds:

- `models/staging/<name>/_<name>__sources.yml`
- `models/staging/<name>/_<name>__models.yml`
- `models/staging/<name>/stg_<name>__records.sql`

The command does not overwrite files that already exist.

## Recommended workflow

Use `init` to create the baseline project, then add new marts and sources as the repo grows. The generated SQL and YAML are stubs, so plan to adapt them to your real warehouse and naming conventions.
