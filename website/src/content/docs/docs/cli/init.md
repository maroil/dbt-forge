---
title: init
description: Command reference for scaffolding a new dbt project with dbt-forge.
---

`dbt-forge init` scaffolds a new dbt project. Use it when you want a consistent
starting structure instead of building folders and setup files by hand.

## Command

```bash
dbt-forge init [PROJECT_NAME] [--defaults] [--output PATH] [--dry-run]
```

## What it does

The command:

- collects configuration through interactive prompts or `--defaults`
- scaffolds a dbt project directory with core files and optional setup files
- prints the next local commands to run after the scaffold is written

## Arguments

### `PROJECT_NAME`

Optional project name for the generated dbt project.

- When omitted in interactive mode, the CLI prompts for it.
- Names are slugified to lowercase with underscores.

## Important options

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
- example snapshot
- example seed
- example exposure
- example macro

## Generated output

The command creates a dbt project directory with:

- `dbt_project.yml`
- `profiles/profiles.yml`
- `models/`, `tests/`, `macros/`, `selectors.yml`
- optional `.sqlfluff`
- optional CI files
- optional example staging, marts, and tests
- optional `snapshots/example_snapshot.sql`
- optional `seeds/example_seed.csv` and `seeds/_example_seed__seeds.yml`
- optional `models/marts/__example__exposures.yml`
- optional `macros/example_macro.sql`

## Behavior and limits

- `--dry-run` still resolves the full config and project path, but it does not write files.
- The command always prints a banner and next-step hints for the generated project.
