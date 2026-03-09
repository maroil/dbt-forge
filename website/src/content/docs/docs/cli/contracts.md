---
title: contracts
description: Command reference for generating dbt data contracts from warehouse metadata.
---

`dbt-forge contracts generate` creates dbt data contracts (v1.5+) by introspecting
column types from your warehouse. Use it to enforce schema stability on public models
without writing contract YAML by hand.

## Command

```bash
dbt-forge contracts generate [MODEL] [--all-public] [--dry-run] [--yes] [--target TARGET]
```

## What it does

The command connects to your warehouse, reads column names, data types, and
nullability for each model, then updates the model's YAML file with:

- `contract: { enforced: true }` in the model config
- `data_type` on each column
- `not_null` test for non-nullable columns (if not already present)

Existing descriptions, tests, and other YAML content are preserved.

## Arguments

### `MODEL`

Generate a contract for a specific model.

```bash
dbt-forge contracts generate orders
```

## Options

### `--all-public`

Generate contracts for all models with `access: public` defined in YAML.

```bash
dbt-forge contracts generate --all-public
```

### `--dry-run`

Preview the generated YAML without writing to disk.

```bash
dbt-forge contracts generate orders --dry-run
```

### `--yes`, `-y`

Auto-accept all generated contracts without interactive review.

```bash
dbt-forge contracts generate --all-public --yes
```

### `--target`

dbt profile target for the warehouse connection. Defaults to `dev`.

```bash
dbt-forge contracts generate orders --target prod
```

## Interactive review

When run without `--yes`, the command presents each generated contract for review.
You can accept or skip each model, following the same pattern as `docs generate`.

## Generated output

For a model `orders` with columns `id (INTEGER, NOT NULL)`, `amount (NUMERIC, NULL)`,
and `created_at (TIMESTAMP, NOT NULL)`:

```yaml
version: 2
models:
  - name: orders
    config:
      contract:
        enforced: true
    columns:
      - name: id
        data_type: INTEGER
        data_tests:
          - not_null
      - name: amount
        data_type: NUMERIC
      - name: created_at
        data_type: TIMESTAMP
        data_tests:
          - not_null
```

## Finding public models

The `--all-public` flag scans all YAML files under `models/` for models with
`access: public` (either at the top level or inside `config:`). This follows the
dbt Mesh convention where public models are the contract boundary between projects.

## Behavior and limits

- Must run from inside an existing dbt project (walks up to find `dbt_project.yml`).
- Reads connection credentials from `profiles.yml` using the `introspect` module.
- Requires the model to exist in the warehouse (the table/view must be queryable).
- Schema is inferred from the model's directory path (e.g., `models/staging/` uses schema `staging`).
- If the YAML file already exists, existing content (descriptions, tests, other models) is preserved.
- If the YAML file does not exist, a new file is created with `version: 2`.
- The `not_null` test is only added for non-nullable columns and only if not already present.
- Supported warehouses: all 8 adapters (BigQuery, Snowflake, PostgreSQL, DuckDB, Databricks, Redshift, Trino, Spark).
