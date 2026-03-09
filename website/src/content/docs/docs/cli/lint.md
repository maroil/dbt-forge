---
title: lint
description: Command reference for linting dbt project structure against architectural rules.
---

`dbt-forge lint` checks your dbt project for architectural issues that go beyond SQL
syntax. Use it to catch DAG problems, complexity violations, and YAML-SQL drift before
they become production headaches.

## Command

```bash
dbt-forge lint [--rule NAME] [--ci] [--config PATH]
```

## What it does

The command runs 6 architectural lint rules against the current dbt project. It builds
a dependency graph from `ref()` and `source()` calls in your SQL, then checks for
structural issues that static SQL linters miss.

All checks are file-based and do not require a warehouse connection.

## Options

### `--rule`, `-r`

Run a specific rule only instead of all rules.

```bash
dbt-forge lint --rule fan-out
dbt-forge lint --rule complexity
```

Valid rule names: `fan-out`, `source-to-mart`, `complexity`, `duplicate-logic`,
`circular-deps`, `yaml-sql-drift`.

### `--ci`

Exit with code 1 if any rule produces warnings. Use this in CI pipelines.

```bash
dbt-forge lint --ci
```

### `--config`

Path to a custom lint configuration file. If not specified, the command looks for
`.dbt-forge-lint.yml` in the project root. If no config file exists, default
thresholds are used.

```bash
dbt-forge lint --config ./custom-lint.yml
```

## Rules

| Rule | What it checks |
|------|----------------|
| `fan-out` | Models with downstream dependents >= threshold (default: 5) |
| `source-to-mart` | Models in `marts/` that reference `source()` directly instead of staging models |
| `complexity` | CTE count, JOIN count, or line count exceeding configured thresholds |
| `duplicate-logic` | Identical CTE bodies appearing in multiple models |
| `circular-deps` | Circular `ref()` dependencies in the DAG |
| `yaml-sql-drift` | Columns defined in YAML that do not match the SQL `SELECT` clause |

### Rule details

**fan-out** -- Models with too many downstream dependents create fragile DAGs. When a
high fan-out model changes, many downstream models need to be rebuilt and tested. The
default threshold is 5. Lower it for stricter checks.

**source-to-mart** -- Marts should reference staging or intermediate models, not raw
sources directly. A mart referencing `source()` bypasses the staging layer where
cleaning and renaming should happen.

**complexity** -- Models with many CTEs (default: 8), JOINs (default: 6), or lines
(default: 300) are harder to maintain. Split complex models into intermediate models.

**duplicate-logic** -- CTE bodies that appear identically in multiple models indicate
shared logic that should be extracted into a separate model or macro.

**circular-deps** -- Circular `ref()` references prevent dbt from building the DAG.
The rule uses depth-first search to detect cycles.

**yaml-sql-drift** -- Columns listed in YAML schema files should match the columns
in the SQL `SELECT` clause. Drift happens when SQL is modified but the YAML is not
updated, or vice versa.

## Configuration

Create `.dbt-forge-lint.yml` in your project root to customize thresholds:

```yaml
fan_out_threshold: 5
max_cte_count: 8
max_join_count: 6
max_line_count: 300
disabled_rules:
  - duplicate-logic
```

All fields are optional. Missing values use the defaults shown above.

## Output

The command displays results using the same table format as `doctor`:

```
                    dbt-forge lint
 Status   Rule               Details
 PASS     fan-out            No models exceed fan-out threshold.
 WARN     source-to-mart     fct_orders references source() directly.
 PASS     complexity         All models within complexity limits.
 PASS     duplicate-logic    No duplicate CTE bodies found.
 PASS     circular-deps      No circular dependencies detected.
 WARN     yaml-sql-drift     stg_orders: YAML has columns not in SQL: [email]

  4 passed, 2 warnings
```

## CI integration

```yaml
# GitHub Actions
- name: Lint dbt project
  run: dbt-forge lint --ci
```

## Behavior and limits

- Must run from inside an existing dbt project (walks up to find `dbt_project.yml`).
- Builds the dependency graph from `ref()` and `source()` regex patterns in SQL files.
- The `yaml-sql-drift` rule extracts columns from the final `SELECT` clause using regex. Complex SQL with dynamic columns or `SELECT *` may not be fully parsed.
- The `duplicate-logic` rule ignores trivial CTEs (under 20 characters) to avoid false positives.
- Disabled rules in the config file are skipped entirely.
