---
title: add
description: Command reference for adding marts, sources, snapshots, seeds, exposures, and macros to an existing dbt project.
---

`dbt-forge add` extends an existing dbt project. Use it when the starting structure is
already in place and you want to scaffold a new component without creating files by hand.

## Commands

```bash
dbt-forge add mart NAME
dbt-forge add source NAME
dbt-forge add snapshot NAME
dbt-forge add seed NAME
dbt-forge add exposure NAME
dbt-forge add macro NAME
```

## What it does

- `add mart` scaffolds a new mart directory with starter SQL and YAML files.
- `add source` scaffolds a new staging directory with source YAML and a starter model.
- `add snapshot` scaffolds a snapshot SQL file with a timestamp strategy stub.
- `add seed` scaffolds a CSV stub and a seeds YAML file with column descriptions and tests.
- `add exposure` scaffolds an exposure YAML file for documenting a downstream dashboard or report.
- `add macro` scaffolds a macro SQL file with a named macro block stub.
- All commands leave existing files in place.

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

## `add snapshot`

```bash
dbt-forge add snapshot orders
```

This scaffolds:

- `snapshots/<name>.sql`

The generated file contains a `{% snapshot %}` block configured with the `timestamp`
strategy. Update the `unique_key`, `updated_at`, and source reference to match your data.

The command does not overwrite files that already exist.

## `add seed`

```bash
dbt-forge add seed dim_country
```

This scaffolds:

- `seeds/<name>.csv` — a three-column CSV stub (`id`, `name`, `created_at`)
- `seeds/_<name>__seeds.yml` — YAML with column descriptions and `unique`/`not_null` tests

Replace the CSV stub with your actual reference data before running `dbt seed`.

The command does not overwrite files that already exist.

## `add exposure`

```bash
dbt-forge add exposure weekly_revenue
```

This scaffolds:

- `models/marts/__<name>__exposures.yml`

The generated file declares a dashboard exposure with `type: dashboard`,
`maturity: medium`, a placeholder `depends_on` reference, and an owner block.
Update all fields to reflect the real downstream tool and team.

The command does not overwrite files that already exist.

## `add macro`

```bash
dbt-forge add macro cents_to_dollars
```

This scaffolds:

- `macros/<name>.sql`

The generated file contains a named `{% macro %}` block with a placeholder body.
Add your macro logic inside the block.

The command does not overwrite files that already exist.

## Behavior and limits

- Commands must run inside an existing dbt project.
- Existing files are not overwritten.
- The generated SQL and YAML are starter files and should be adapted to the real warehouse, source schema, and naming rules used by the project.

## Recommended workflow

Use `init` to scaffold the starting structure, then use `add` commands as the dbt
project grows into new domains, source systems, or analytical artifacts.
