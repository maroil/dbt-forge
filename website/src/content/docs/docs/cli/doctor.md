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

## Options

### `--check`, `-c`

Run a specific check only instead of all checks.

```bash
dbt-forge doctor --check naming-conventions
dbt-forge doctor --check test-coverage
```

### `--fix`

Auto-fix issues where possible. Currently generates missing schema YAML stubs for
undocumented models.

```bash
dbt-forge doctor --fix
```

### `--ci`

Non-interactive mode for CI pipelines. Exits with code 1 if any check fails.

```bash
dbt-forge doctor --ci
```

## Checks

| Check | What it validates |
|-------|-------------------|
| `naming-conventions` | Staging models prefixed `stg_`, intermediates prefixed `int_` |
| `schema-coverage` | Every SQL model has a corresponding YAML entry |
| `test-coverage` | Every model has at least one test defined |
| `hardcoded-refs` | No hardcoded `database.schema.table` references in model SQL |
| `packages-pinned` | All entries in `packages.yml` have version ranges |
| `source-freshness` | Sources have `freshness` config defined |
| `orphaned-yml` | No YAML model entries referencing non-existent SQL files |
| `sqlfluff-config` | `.sqlfluff` config file exists |
| `gitignore` | `.gitignore` includes `target/`, `dbt_packages/`, `logs/` |
| `disabled-models` | No models with `enabled: false` (tech debt indicator) |

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

## CI integration

Use `--ci` in CI pipelines to fail the build when checks don't pass:

```yaml
# GitHub Actions example
- name: dbt-forge doctor
  run: dbt-forge doctor --ci
```

## Behavior and limits

- Must run from inside an existing dbt project (walks up to find `dbt_project.yml`).
- Intermediate models (`int_` prefix) are excluded from schema coverage checks since they are typically ephemeral.
- The `--fix` flag only generates missing schema stubs. Other fixes require manual intervention.
- Checks are fast and do not require a warehouse connection.
