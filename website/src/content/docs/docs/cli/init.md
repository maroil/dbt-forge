---
title: init
description: Reference for the dbt-forge init command.
---

## Synopsis

```bash
dbt-forge init [PROJECT_NAME] [--defaults] [--output PATH] [--dry-run]
```

## Arguments

### `PROJECT_NAME`

Optional project name for the generated dbt project.

- When omitted in interactive mode, the CLI prompts for it.
- Names are slugified to lowercase with underscores.

## Options

### `--defaults`, `-d`

Skip interactive prompts and use the current default configuration.

### `--output`, `-o`

Choose the directory where the project folder should be created.

```bash
dbt-forge init analytics_core --defaults --output ./sandbox
```

### `--dry-run`

Show the files that would be written without creating anything on disk.

## Interactive prompts

Without `--defaults`, `init` currently asks for:

- project name
- warehouse adapter
- marts to scaffold
- starter packages
- example models and tests
- SQLFluff config
- CI providers
- dbt unit test examples
- MetricFlow semantic model examples

## Generated output

The command creates a dbt project directory with:

- `dbt_project.yml`
- `profiles/profiles.yml`
- `models/`, `tests/`, `macros/`, `selectors.yml`
- optional `.sqlfluff`
- optional CI files
- optional example staging, marts, and tests

## Notes

- `--dry-run` still resolves the full config and project path, but it does not write files.
- The command always prints a banner and next-step hints for the generated project.
