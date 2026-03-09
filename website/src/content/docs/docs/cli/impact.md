---
title: impact
description: Command reference for analyzing downstream impact of model changes.
---

`dbt-forge impact` shows which models are affected when you change an upstream model.
Use it to understand blast radius before merging changes and to communicate risk in
pull requests.

## Command

```bash
dbt-forge impact <MODEL> [--diff] [--base REF] [--pr]
```

## What it does

The command builds a dependency graph from `ref()` and `source()` calls in your SQL,
then computes the downstream impact of one or more changed models. It shows:

- A tree of all affected downstream models, colored by depth
- Blast radius: how many models are impacted as a percentage of the total project
- Direct vs transitive impact counts
- Untested impacted models (models without any tests defined)

## Arguments

### `MODEL`

The model name to analyze. Shows all downstream dependents as a Rich tree.

```bash
dbt-forge impact stg_orders
```

## Options

### `--diff`

Auto-detect changed models from `git diff` instead of specifying a model name.
Compares the current branch against the base ref.

```bash
dbt-forge impact --diff
dbt-forge impact --diff --base develop
```

### `--base`

Base git ref for `--diff` comparison. Defaults to `main`.

```bash
dbt-forge impact --diff --base origin/main
```

### `--pr`

Output markdown formatted for pull request descriptions. Includes a summary table
with blast radius, impacted model counts, and untested model warnings.

```bash
dbt-forge impact stg_orders --pr
dbt-forge impact --diff --pr
```

## Output

### Tree view (default)

```
stg_orders
├── fct_orders (direct)
│   └── rpt_revenue (transitive)
└── fct_order_items (direct)

Blast radius: 66.7% (2 of 3 models impacted)
Direct: 2  Transitive: 1  Untested: 1
```

### PR markdown (`--pr`)

```markdown
## Impact Analysis

**Changed models:** `stg_orders`

| Metric | Value |
|--------|-------|
| Total impacted | 2 |
| Direct | 1 |
| Transitive | 1 |
| Blast radius | 66.7% |

### Untested impacted models
- `rpt_revenue`
```

## Behavior and limits

- Must run from inside an existing dbt project (walks up to find `dbt_project.yml`).
- Builds the graph from `ref()` and `source()` regex patterns in SQL files.
- The `--diff` flag uses `git diff --name-only {base}...HEAD -- models/` to detect changed `.sql` files.
- Models not found in the graph (typos, non-existent models) produce an error message without crashing.
- Untested models are detected by scanning YAML files for `data_tests:` entries.
- If no model is specified and `--diff` is not set, the command prints a usage error.
