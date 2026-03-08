---
title: Getting started
description: Install dbt-forge and scaffold a new dbt project with the current CLI.
---

This site documents the `0.1.x` alpha line of the `dbt-forge` CLI.

## Supported Python

- Python 3.11
- Python 3.12
- Python 3.13

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

## Extend an existing project

Inside a dbt project, use the `add` subcommands to scaffold new sections without
overwriting files that already exist:

```bash
dbt-forge add mart finance
dbt-forge add source salesforce
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

## Release scope

- The package is published to PyPI from GitHub Actions on `v*` tags.
- The website is the CLI documentation and marketing site; it is not a separately versioned
  release artifact.
