---
title: doctor
description: Command reference for running project health checks on an existing dbt project.
---

`dbt-forge doctor` scans an existing dbt project and validates it against common best
practices. Use it to catch issues before they cause production failures.

## Command

```bash
dbt-forge doctor [--check NAME] [--fix] [--ci]
```

## What it does

The command runs 10 health checks on the current dbt project and displays a summary
table with pass/fail status and actionable fix suggestions for each check.

All checks are file-based and do not require a warehouse connection.

## Options

### `--check`, `-c`

Run a specific check only instead of all checks.

```bash
dbt-forge doctor --check naming-conventions
dbt-forge doctor --check test-coverage
```

Valid check names: `naming-conventions`, `schema-coverage`, `test-coverage`,
`hardcoded-refs`, `packages-pinned`, `source-freshness`, `orphaned-yml`,
`sqlfluff-config`, `gitignore`, `disabled-models`.

### `--fix`

Auto-fix issues where possible. Currently generates missing schema YAML stubs for
undocumented models. For each model without a YAML entry, `--fix` creates a file
at `models/<layer>/_<model_name>__models.yml` with a model name and description
placeholder.

```bash
dbt-forge doctor --fix
```

Example output:

```
 Created models/marts/finance/_fct_revenue__models.yml
 Created models/staging/stripe/_stg_stripe__orders__models.yml

  8 passed, 0 failed
```

Other failing checks are not auto-fixed and require manual intervention.

### `--ci`

Non-interactive mode for CI pipelines. Exits with code 1 if any check fails,
code 0 if all checks pass.

```bash
dbt-forge doctor --ci
```

## Checks

| Check | What it validates |
|-------|-------------------|
| `naming-conventions` | Staging models prefixed `stg_`, intermediates prefixed `int_` |
| `schema-coverage` | Every SQL model has a corresponding YAML entry |
| `test-coverage` | Every model has at least one test defined |
| `hardcoded-refs` | No hardcoded `database.schema.table` patterns in model SQL |
| `packages-pinned` | All entries in `packages.yml` have version ranges |
| `source-freshness` | Sources have `freshness` config defined |
| `orphaned-yml` | No YAML model entries referencing non-existent SQL files |
| `sqlfluff-config` | `.sqlfluff` config file exists |
| `gitignore` | `.gitignore` includes `target/`, `dbt_packages/`, `logs/` |
| `disabled-models` | No models with `enabled: false` (tech debt indicator) |

### Check details

**naming-conventions** — Models in `models/staging/` must start with `stg_`. Models
in `models/intermediate/` must start with `int_`. Models in other directories are
not checked.

**schema-coverage** — Every `.sql` file in `models/` should have a matching entry in
a `models:` section of a YAML file. Intermediate models (`int_` prefix) are excluded
from this check since they are typically ephemeral and do not need schema documentation.

**test-coverage** — Every model should have at least one test (column-level or data test)
defined in a YAML file. The check looks for `data_tests:` or `tests:` entries under
model columns.

**hardcoded-refs** — Scans SQL files for patterns like `database.schema.table` that
bypass `ref()` and `source()`. These break cross-environment portability.

**packages-pinned** — Checks that all packages in `packages.yml` use version ranges
(`version:`) rather than unpinned git references.

**source-freshness** — Every source in `*sources*.yml` files should define a
`freshness:` block with `warn_after` and/or `error_after`.

**orphaned-yml** — YAML model entries that reference a SQL file that does not exist.
These accumulate when models are renamed or deleted without updating the YAML.

**disabled-models** — Models with `config(enabled=false)` or `enabled: false` in YAML.
These are tech debt — either remove the model or re-enable it.

## Output

The command displays a Rich table with pass/fail status per check:

```
                    dbt-forge doctor
 Status   Check                Details
 PASS     naming-conventions   All models follow naming conventions.
 PASS     schema-coverage      All models have YAML documentation.
 FAIL     test-coverage        2 model(s) have no tests:
                                 models/marts/finance/fct_revenue.sql
                               Use dbt-forge add test <model> to generate test stubs.
 PASS     packages-pinned      All packages have version ranges.

  8 passed, 2 failed
```

Each failing check includes the affected file paths and a suggested fix.

## CI integration

Use `--ci` in CI pipelines to fail the build when checks don't pass:

```yaml
# GitHub Actions example
- name: dbt-forge doctor
  run: dbt-forge doctor --ci
```

```yaml
# GitLab CI example
doctor:
  script:
    - dbt-forge doctor --ci
```

## Behavior and limits

- Must run from inside an existing dbt project (walks up from the current directory to find `dbt_project.yml`).
- Intermediate models (`int_` prefix) are excluded from schema coverage checks since they are typically ephemeral.
- The `--fix` flag only generates missing schema stubs. Other fixes require manual intervention.
- Checks are fast and do not require a warehouse connection — all data comes from local files.
- When using `--check`, only the specified check runs. The exit code in `--ci` mode reflects only that check.
