---
title: add
description: Command reference for adding marts and sources to an existing dbt project.
---

`dbt-forge add` extends an existing dbt project. Use it when the starting structure is
already in place and you want to scaffold a new mart or source without creating files by hand.

## Commands

```bash
dbt-forge add mart NAME
dbt-forge add source NAME
```

## What it does

- `add mart` scaffolds a new mart directory with starter SQL and YAML files.
- `add source` scaffolds a new staging directory with source YAML and a starter model.
- Both commands leave existing files in place.

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

## Behavior and limits

- Commands must run inside an existing dbt project.
- Existing files are not overwritten.
- The generated SQL and YAML are starter files and should be adapted to the real warehouse, source schema, and naming rules used by the project.

## Recommended workflow

Use `init` to scaffold the starting structure, then use `add` commands as the dbt
project grows into new domains and source systems.
