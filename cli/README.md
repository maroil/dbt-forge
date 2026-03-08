# dbt-forge

`dbt-forge` is a Python CLI for scaffolding opinionated dbt projects with a consistent
layout, starter models, adapter-specific profiles, and optional CI / SQLFluff setup.
The project is currently in its `0.1.x` alpha phase.

## Features

- `src/`-packaged Python CLI built on Typer and Rich
- Interactive or default-driven project generation
- Adapter templates for BigQuery, Snowflake, PostgreSQL, DuckDB, Databricks, Redshift, Trino, and Spark
- `add mart` and `add source` commands for extending an existing dbt project
- Optional starter dbt packages, SQLFluff config, and CI templates
- Generated `.env` support so local dbt commands resolve `profiles/` consistently

## Install

```bash
pip install dbt-forge
```

Or with `uv`:

```bash
uv tool install dbt-forge
```

## Quickstart

```bash
dbt-forge init
```

For a non-interactive scaffold:

```bash
dbt-forge init my_dbt_project --defaults
```

Add a mart or source inside an existing dbt project:

```bash
dbt-forge add mart finance
dbt-forge add source salesforce
```

## Supported Python

- Python 3.11
- Python 3.12
- Python 3.13

## Local Development

```bash
cd cli
uv sync --all-groups
uv run pre-commit install --hook-type commit-msg
uv run ruff check .
uv run pytest
uv build
uvx twine check dist/*
```

## Commit Messages

This repo uses Conventional Commits. Every commit message must start with a type such as:

- `feat: add databricks profile scaffolding`
- `fix: handle missing target directory`
- `chore: refresh release workflow`

The local `commit-msg` hook enforces this after you run:

```bash
uv run pre-commit install --hook-type commit-msg
```

## Release Process

The package publishes from GitHub Actions on `v*` tags. The website in this repo is
supporting docs/marketing and is not a separately versioned release artifact.

1. Update `src/dbt_forge/__init__.py` if the version changes.
2. Add release notes to the repository `CHANGELOG.md`.
3. Run the release-candidate checks.
4. Run the manual TestPyPI preflight from the `Release` workflow.
5. Push a tag in the form `vX.Y.Z`.
6. Let GitHub Actions publish the artifact to PyPI via Trusted Publishing.

For the detailed checklist and publish prerequisites, see
[`RELEASING.md`](https://github.com/maroil/dbt-forge/blob/main/RELEASING.md).

## Publishing Setup

- Public repo: [maroil/dbt-forge](https://github.com/maroil/dbt-forge)
- Configure GitHub environments named `pypi` and `testpypi`
- Register the GitHub repo as a Trusted Publisher in PyPI and TestPyPI

## License

MIT. See [LICENSE](LICENSE).
