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

All `add` commands must run from inside an existing dbt project. The CLI walks upward
from the current directory until it finds `dbt_project.yml`.

If no dbt project is found, the command exits with an error. You can run `add` from any
subdirectory of the project — it does not need to be the project root.

---

## `add mart`

```bash
dbt-forge add mart finance
```

Scaffolds:

- `models/marts/finance/finance_orders.sql` — mart model stub
- `models/marts/finance/__finance__models.yml` — YAML with model name and description placeholder
- `models/intermediate/finance/int_finance__orders_enriched.sql` — intermediate model stub

## `add source`

```bash
dbt-forge add source salesforce
```

Scaffolds:

- `models/staging/salesforce/_salesforce__sources.yml` — source definition with a sample table
- `models/staging/salesforce/_salesforce__models.yml` — YAML entry for the staging model
- `models/staging/salesforce/stg_salesforce__records.sql` — staging model referencing the source

## `add snapshot`

```bash
dbt-forge add snapshot orders
```

Scaffolds:

- `snapshots/orders.sql`

The generated file contains a `{% snapshot %}` block configured with the `timestamp`
strategy. Update the `unique_key`, `updated_at`, and source reference to match your data.

## `add seed`

```bash
dbt-forge add seed dim_country
```

Scaffolds:

- `seeds/dim_country.csv` — a three-column CSV stub (`id`, `name`, `created_at`)
- `seeds/_dim_country__seeds.yml` — YAML with column descriptions and `unique`/`not_null` tests

## `add exposure`

```bash
dbt-forge add exposure weekly_revenue
```

Scaffolds:

- `models/marts/__weekly_revenue__exposures.yml`

The generated file declares a dashboard exposure with `type: dashboard`,
`maturity: medium`, a placeholder `depends_on` reference, and an owner block.

## `add macro`

```bash
dbt-forge add macro cents_to_dollars
```

Scaffolds:

- `macros/cents_to_dollars.sql`

The generated file contains a named `{% macro %}` block with a placeholder body.

---

## `add model`

```bash
dbt-forge add model users
```

Interactively scaffolds a new dbt model with SQL and YAML. Prompts for:

- **Layer**: staging, intermediate, or marts
- **Materialization**: view, table, incremental, or ephemeral
- **Source** (staging only): auto-detected from existing source YAML files, or entered manually
- **Description**: model-level description
- **Columns**: optional interactive loop to define column names, descriptions, and tests

### Layer defaults

| Layer | Default materialization | Name prefix | Directory |
|-------|------------------------|-------------|-----------|
| staging | view | `stg_<source>__` | `models/staging/<source>/` |
| intermediate | ephemeral | `int_` | `models/intermediate/` |
| marts | table | (none) | `models/marts/` |

### Source auto-detection

For staging models, the CLI scans `models/**/*sources*.yml` and `models/**/*sources*.yaml`
for defined source names. If sources are found, it presents a selection list:

```
? Source name:
> stripe
  salesforce
  Other (enter manually)
```

If no sources are found or "Other" is selected, the CLI falls back to a text prompt.

### Generated files

For a staging model named `users` with source `stripe`:

- `models/staging/stripe/stg_stripe__users.sql` — SQL with `source('stripe', 'users')`
- `models/staging/stripe/_stg_stripe__users__models.yml` — YAML entry with columns and tests

For incremental models, the SQL includes an `is_incremental()` block:

```sql
{{
    config(
        materialized='incremental',
        unique_key='id'
    )
}}

select * from {{ ref('upstream_model') }}

{% if is_incremental() %}
where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

### Column definition

When adding columns interactively, each column prompts for:

- Column name
- Description
- Tests to apply: `unique`, `not_null`, `accepted_values`, `relationships`

## `add test`

```bash
dbt-forge add test stg_orders
```

Scaffolds a test for an existing model. Prompts for test type:

### Data test

Generates `tests/assert_stg_orders_valid.sql` with a SQL assertion stub that references
the model via `ref()`.

### Unit test (dbt 1.8+)

Generates `tests/unit/test_stg_orders.yml` with a mock-based unit test:

```yaml
unit_tests:
  - name: test_stg_orders
    model: stg_orders
    given:
      - input: ref('stg_orders')
        rows:
          - {id: 1, amount: 100}
    expect:
      rows:
        - {id: 1, amount: 100}
```

### Schema test (column-level in `.yml`)

Generates `models/_stg_orders__tests.yml` with column-level tests. The flow:

1. **Column detection** — scans existing `models/**/*.yml` for the model's column definitions.
   If found, presents a checkbox to select columns. If not found, prompts for comma-separated
   column names.

2. **Test selection** — for each column, prompts for test types:
   - `unique` — column values are unique
   - `not_null` — no null values
   - `accepted_values` — prompts for a comma-separated list of allowed values
   - `relationships` — prompts for the referenced model name and field

3. **Output** — generates a YAML file:

```yaml
version: 2

models:
  - name: stg_orders
    columns:
      - name: id
        data_tests:
          - unique
          - not_null
      - name: status
        data_tests:
          - accepted_values:
              values: ['active', 'inactive', 'archived']
      - name: customer_id
        data_tests:
          - relationships:
              to: ref('dim_customers')
              field: id
```

## `add ci`

```bash
dbt-forge add ci github
dbt-forge add ci gitlab
dbt-forge add ci bitbucket
dbt-forge add ci              # interactive prompt
```

Scaffolds CI/CD pipeline config for an existing dbt project. Reuses the same templates
used during `init`. Auto-detects the adapter from `profiles/profiles.yml`.

Provider arguments (case-insensitive):

| Argument | Provider | Generated file |
|----------|----------|----------------|
| `github` | GitHub Actions | `.github/workflows/dbt_ci.yml` |
| `gitlab` | GitLab CI | `.gitlab-ci.yml` |
| `bitbucket` | Bitbucket Pipelines | `bitbucket-pipelines.yml` |

Without an argument, the CLI shows a multi-select prompt. Skips if the CI config file
already exists.

## `add package`

```bash
dbt-forge add package dbt-utils
dbt-forge add package --list     # browse available packages
dbt-forge add package            # interactive selection
```

Adds a dbt package to `packages.yml` from a curated registry with known-good version
ranges. Parses the existing YAML, appends the new entry, and writes it back.

### Available packages

| Package | Hub path |
|---------|----------|
| dbt-utils | dbt-labs/dbt_utils |
| dbt-expectations | metaplane/dbt_expectations |
| dbt-codegen | dbt-labs/codegen |
| elementary | elementary-data/elementary |
| dbt-audit-helper | dbt-labs/audit_helper |
| dbt-project-evaluator | dbt-labs/dbt_project_evaluator |
| dbt-meta-testing | tnightengale/dbt_meta_testing |
| dbt-date | calogica/dbt_date |
| dbt-profiler | data-mie/dbt_profiler |
| re-data | re-data/dbt_re_data |
| dbt-artifacts | brooklyn-data/dbt_artifacts |
| dbt-external-tables | dbt-labs/dbt_external_tables |
| metrics | dbt-labs/metrics |
| dbt-activity-schema | bcodell/dbt_activity_schema |
| dbt-constraints | Snowflake-Labs/dbt_constraints |
| dbt-privacy | pvcy/dbt_privacy |
| dbt-unit-testing | EqualExperts/dbt-unit-testing |
| dbt-fivetran-utils | fivetran/fivetran_utils |
| dbt-snowplow-web | snowplow/dbt_snowplow_web |
| dbt-segment | dbt-labs/segment |

Use `--list` to see all packages and their hub paths in the terminal.

### Package config generation

Some packages need configuration in `dbt_project.yml`. When you add one of these
packages, the CLI automatically merges the required `vars` into `dbt_project.yml`:

| Package | Config added to `dbt_project.yml` |
|---------|-----------------------------------|
| elementary | `vars: { elementary: { edr_cli_run: "true" } }` |
| dbt-project-evaluator | `vars: { dbt_project_evaluator: { documentation_coverage_target: 100, test_coverage_target: 100 } }` |

If `dbt_project.yml` does not exist or is not parseable, the config step is skipped
with a warning.

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

- All commands must run inside an existing dbt project (any directory containing or beneath `dbt_project.yml`).
- Existing files are not overwritten (except `add package`, which appends to `packages.yml`, and package config which merges into `dbt_project.yml`).
- Interactive commands (`add model`, `add test`, `add ci`, `add package`) require a terminal.
- The generated SQL and YAML are starter files and should be adapted to the real warehouse, source schema, and naming rules used by the project.
- Run `dbt-forge add --help` for a summary of all subcommands.

## Recommended workflow

Use `init` to scaffold the starting structure, then use `add` commands as the dbt
project grows into new domains, source systems, or analytical artifacts. Use
[`doctor`](/docs/cli/doctor/) to validate that the project follows best practices as it
evolves.
