---
title: Getting started
description: Install dbt-forge, scaffold a dbt project, and run the first local dbt commands.
---

`dbt-forge` is a Python CLI for scaffolding a dbt project with a consistent starting
structure. This guide covers the current `0.1.x` alpha line of the CLI.

## Supported Python

- Python 3.11
- Python 3.12
- Python 3.13

## Install

Install `dbt-forge` with either `pip` or `uv`.

```bash
pip install dbt-forge
```

```bash
uv tool install dbt-forge
```

## Initialize a dbt project

Run the interactive flow when you want to choose the adapter, starter marts, packages,
and optional setup files:

```bash
dbt-forge init
```

Use defaults when you want a repeatable starting structure without prompts:

```bash
dbt-forge init my_dbt_project --defaults
```

Preview the scaffold without writing files:

```bash
dbt-forge init my_dbt_project --defaults --dry-run
```

## Inspect the generated project

The exact output depends on the options you choose. A typical scaffold includes:

- `dbt_project.yml`
- `profiles/profiles.yml`
- `models/staging/`, `models/intermediate/`, and `models/marts/`
- `tests/`, `macros/`, and `selectors.yml`
- optional files such as `.sqlfluff` and CI configuration

Use [Project structure](/docs/project-structure/) for a fuller breakdown of the generated layout.

## Run the next commands

After the scaffold is written, move into the new dbt project and run the local setup commands:

```bash
cd my_dbt_project
uv sync
uv run --env-file .env dbt deps
uv run --env-file .env dbt debug
```

If you skip starter packages during `init`, `dbt deps` is not required.

## Extend an existing project

Inside an existing dbt project, use the `add` subcommands to scaffold new sections
without overwriting files that already exist:

```bash
dbt-forge add mart finance
dbt-forge add source salesforce
```

## Default selections

When you use `--defaults`, the CLI currently selects:

- `BigQuery` as the adapter
- `finance` and `marketing` as starter marts
- `dbt-utils` and `dbt-expectations` as starter packages
- example models and tests enabled
- SQLFluff enabled
- GitHub Actions enabled

Treat those defaults as a starting point. Review the generated models, packages, and CI
files before committing them to a team project.
