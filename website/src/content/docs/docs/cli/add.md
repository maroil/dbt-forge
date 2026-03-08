---
title: add
description: Command reference for adding components to an existing dbt project — marts, sources, models, tests, CI, packages, and more.
---

`dbt-forge add` extends an existing dbt project. Use it when the starting structure is
already in place and you want to scaffold a new component without creating files by hand.

## Commands

```bash
# Scaffold components
dbt-forge add mart NAME
dbt-forge add source NAME
dbt-forge add snapshot NAME
dbt-forge add seed NAME
dbt-forge add exposure NAME
dbt-forge add macro NAME

# Interactive generators
dbt-forge add model NAME
dbt-forge add test MODEL_NAME
dbt-forge add ci [PROVIDER]
dbt-forge add package [NAME]

# Tooling
dbt-forge add pre-commit
```

## Project detection

All `add` commands must run from inside an existing dbt project. The CLI walks upward from the current directory until it finds `dbt_project.yml`.

If no dbt project is found, the command exits with an error.

---

## `add mart`

```bash
dbt-forge add mart finance
```

Scaffolds:

- `models/marts/<name>/<name>_orders.sql`
- `models/marts/<name>/__<name>__models.yml`
- `models/intermediate/<name>/int_<name>__orders_enriched.sql`

## `add source`

```bash
dbt-forge add source salesforce
```

Scaffolds:

- `models/staging/<name>/_<name>__sources.yml`
- `models/staging/<name>/_<name>__models.yml`
- `models/staging/<name>/stg_<name>__records.sql`

## `add snapshot`

```bash
dbt-forge add snapshot orders
```

Scaffolds:

- `snapshots/<name>.sql`

The generated file contains a `{% snapshot %}` block configured with the `timestamp`
strategy. Update the `unique_key`, `updated_at`, and source reference to match your data.

## `add seed`

```bash
dbt-forge add seed dim_country
```

Scaffolds:

- `seeds/<name>.csv` — a three-column CSV stub (`id`, `name`, `created_at`)
- `seeds/_<name>__seeds.yml` — YAML with column descriptions and `unique`/`not_null` tests

## `add exposure`

```bash
dbt-forge add exposure weekly_revenue
```

Scaffolds:

- `models/marts/__<name>__exposures.yml`

The generated file declares a dashboard exposure with `type: dashboard`,
`maturity: medium`, a placeholder `depends_on` reference, and an owner block.

## `add macro`

```bash
dbt-forge add macro cents_to_dollars
```

Scaffolds:

- `macros/<name>.sql`

The generated file contains a named `{% macro %}` block with a placeholder body.

---

## `add model`

```bash
dbt-forge add model users
```

Interactively scaffolds a new dbt model with SQL and YAML. Prompts for:

- **Layer**: staging, intermediate, or marts (determines directory and name prefix)
- **Materialization**: view, table, incremental, or ephemeral (smart defaults per layer)
- **Source**: for staging models, which source to reference
- **Description**: model-level description
- **Columns**: optional interactive loop to define column names, descriptions, and tests

Generates:

- SQL file with correct naming (`stg_`, `int_`, or mart name) in the right directory
- YAML file with columns, descriptions, tests, and materialization config
- For incremental models: includes an `is_incremental()` block template

Smart defaults: staging uses view, intermediate uses ephemeral, marts uses table.

## `add test`

```bash
dbt-forge add test stg_orders
```

Scaffolds a test for an existing model. Prompts for:

- **Test type**: data test (custom SQL assertion) or unit test (dbt 1.8+ mock-based)

For data tests, generates `tests/assert_<model>_valid.sql` with a SQL assertion stub.
For unit tests, generates `tests/unit/test_<model>.yml` with mock input rows and expected output.

## `add ci`

```bash
dbt-forge add ci github
dbt-forge add ci gitlab
dbt-forge add ci bitbucket
dbt-forge add ci              # interactive prompt
```

Scaffolds CI/CD pipeline config for an existing dbt project. Reuses the same templates
used during `init`. Auto-detects the adapter from `profiles/profiles.yml`.

Supported providers:

- `github` — `.github/workflows/dbt_ci.yml`
- `gitlab` — `.gitlab-ci.yml`
- `bitbucket` — `bitbucket-pipelines.yml`

Skips if the CI config file already exists.

## `add package`

```bash
dbt-forge add package dbt-utils
dbt-forge add package --list     # browse available packages
dbt-forge add package            # interactive selection
```

Adds a dbt package to `packages.yml` from a curated registry of 20 packages with
known-good version ranges. Parses the existing YAML, appends the new entry, and writes
it back.

Available packages include: dbt-utils, dbt-expectations, dbt-codegen, elementary,
dbt-audit-helper, dbt-project-evaluator, dbt-date, dbt-profiler, and more.

Use `--list` to see all available packages and their hub paths.

Skips if the package is already present in `packages.yml`.

## `add pre-commit`

```bash
dbt-forge add pre-commit
```

Scaffolds:

- `.pre-commit-config.yaml` — hooks for trailing whitespace, end-of-file, YAML validation, yamllint, and optionally SQLFluff (auto-detected from `.sqlfluff`)
- `.editorconfig` — consistent formatting rules (UTF-8, LF line endings, 2-space YAML/SQL indent)
- `.sqlfluffignore` — excludes `target/`, `dbt_packages/`, `logs/` (only if `.sqlfluff` exists)

After running, activate the hooks with `pre-commit install`.

---

## Behavior and limits

- All commands must run inside an existing dbt project.
- Existing files are not overwritten (except `add package`, which appends to `packages.yml`).
- Interactive commands (`add model`, `add test`, `add ci`, `add package`) require a terminal.
- The generated SQL and YAML are starter files and should be adapted to the real warehouse, source schema, and naming rules used by the project.

## Recommended workflow

Use `init` to scaffold the starting structure, then use `add` commands as the dbt
project grows into new domains, source systems, or analytical artifacts. Use `doctor`
to validate that the project follows best practices as it evolves.
