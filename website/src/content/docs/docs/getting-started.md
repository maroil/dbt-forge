---
title: Getting started
description: Install dbt-forge and scaffold a new dbt project with the current CLI.
---

## Install

You can install `dbt-forge` with either `pip` or `uv`.

```bash
pip install dbt-forge
```

```bash
uv tool install dbt-forge
```

## Create a project

Run the interactive flow:

```bash
dbt-forge init
```

Or generate a project with defaults:

```bash
dbt-forge init my_dbt_project --defaults
```

Preview the output without writing files:

```bash
dbt-forge init my_dbt_project --defaults --dry-run
```

## Current defaults

When you use `--defaults`, the CLI currently chooses:

- `BigQuery` as the adapter
- `finance` and `marketing` as starter marts
- `dbt-utils` and `dbt-expectations` as starter packages
- example models and tests enabled
- SQLFluff enabled
- GitHub Actions enabled

## After generation

Inside the generated dbt project, the CLI prints the next commands to run. The standard path is:

```bash
cd my_dbt_project
uv sync
uv run --env-file .env dbt deps
uv run --env-file .env dbt debug
```

## Supported Python

- Python 3.11
- Python 3.12
- Python 3.13
