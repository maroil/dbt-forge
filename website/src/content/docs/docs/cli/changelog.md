---
title: changelog
description: Command reference for generating a changelog of model changes between git refs.
---

`dbt-forge changelog generate` detects model changes between two git refs and
classifies them as breaking or non-breaking. Use it to communicate schema changes
to downstream consumers before they discover them in production.

## Command

```bash
dbt-forge changelog generate [--from REF] [--to REF] [--format FORMAT] [--breaking-only] [-o FILE]
```

## What it does

The command runs `git diff` between two refs and analyzes the changes:

- **SQL file changes**: added, deleted, or modified `.sql` model files
- **YAML column changes**: columns added, removed, or type-changed in model YAML files

Each change is classified as breaking or non-breaking:

| Change | Breaking? |
|--------|-----------|
| Model added | No |
| Model modified | No |
| Model deleted | Yes |
| Column added | No |
| Column removed | Yes |
| Column type changed | Yes |

## Options

### `--from`

Starting git ref. Defaults to the latest git tag. If no tags exist, the command
shows an error.

```bash
dbt-forge changelog generate --from v1.0.0
```

### `--to`

Ending git ref. Defaults to `HEAD`.

```bash
dbt-forge changelog generate --from v1.0 --to v2.0
```

### `--format`

Output format: `markdown` (default) or `json`.

```bash
dbt-forge changelog generate --format json
```

### `--breaking-only`

Show only breaking changes. Non-breaking changes are filtered out.

```bash
dbt-forge changelog generate --breaking-only
```

### `-o`, `--output`

Write output to a file instead of stdout.

```bash
dbt-forge changelog generate -o MODEL_CHANGELOG.md
```

## Output

### Markdown (default)

```markdown
# Changelog

## Breaking Changes

- **orders** `column_removed` — Column 'email' removed (`abc1234`)
- **payments** `type_changed` — Column 'amount': INTEGER → VARCHAR (`def5678`)

## Changes

- **customers** `added` — New model (`ghi9012`)
- **orders** `column_added` — Column 'phone' added (VARCHAR) (`abc1234`)
```

### JSON

```json
[
  {
    "model_name": "orders",
    "change_type": "column_removed",
    "details": "Column 'email' removed",
    "is_breaking": true,
    "commit_hash": "abc1234",
    "commit_date": "2024-06-01"
  }
]
```

## Column change detection

When a YAML file is modified between refs, the command:

1. Retrieves the file content at both refs using `git show`
2. Parses the `columns:` section for each model
3. Compares column names and `data_type` values
4. Reports additions, removals, and type changes

Type changes where either the old or new type is empty (unset) are ignored, since
an empty `data_type` means the type was never specified.

## Behavior and limits

- Must run from inside a git repository.
- Uses `git diff --name-status` to detect file changes and `git show` to retrieve file content at refs.
- Only analyzes files under `models/` — changes to macros, tests, or seeds are not tracked.
- YAML files must follow dbt conventions (`models:` key with `columns:` entries).
- The `--from` default uses `git describe --tags --abbrev=0` to find the latest tag.
- Commit hashes and dates are extracted from `git log` for each changed file.
