---
title: status
description: Command reference for the project stats dashboard.
---

`dbt-forge status` displays a terminal dashboard with a summary of the current dbt
project: model counts by layer, test and documentation coverage, sources, and installed
packages.

## Command

```bash
dbt-forge status
```

No flags are needed — the command always prints the full dashboard.

## What it does

The command scans the current dbt project and prints a Rich table with three columns:

- **Models** — count of SQL models broken down by layer (staging, intermediate, marts, other) plus a total
- **Quality** — test coverage percentage, documentation coverage percentage, and source count with freshness status
- **Dependencies** — list of installed packages from `packages.yml`

## Output

```
              Project: my_dbt_project
 Models                Quality              Dependencies
 staging: 12           test coverage: 75%   dbt_utils
 intermediate: 5       doc coverage: 60%    dbt_expectations
 marts: 8              sources: 4           elementary
 other: 2                (freshness: 2)
 total: 27
```

### Models

SQL files are categorized by their directory path:

| Layer | Directory pattern |
|-------|-------------------|
| staging | `models/staging/**/*.sql` |
| intermediate | `models/intermediate/**/*.sql` |
| marts | `models/marts/**/*.sql` |
| other | Any `.sql` file in `models/` not matching the above |

Only layers with at least one model appear in the output.

### Quality

**Test coverage** — percentage of models that have at least one test defined in a
YAML file. Calculated as: `models with tests / total countable models × 100`.

**Doc coverage** — percentage of models that have a corresponding entry in a YAML
`models:` section. Calculated as: `documented models / total countable models × 100`.

Both coverage metrics exclude internal models — files whose names start with `_`
(e.g., `_stg_stripe__models.yml`). These are YAML schema files, not actual models.

**Sources** — total number of sources defined in `*sources*.yml` files, plus how many
of those have a `freshness:` block configured.

### Dependencies

Lists package names from `packages.yml`. Shows `(none)` if no packages are installed.

## Behavior and limits

- Must run from inside an existing dbt project (walks up to find `dbt_project.yml`).
- Does not require a warehouse connection. All data comes from local files.
- The command has no flags or arguments.
