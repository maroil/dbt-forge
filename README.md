# dbt-forge

`dbt-forge` is a Python CLI for scaffolding opinionated dbt projects with a consistent layout, starter models, adapter-specific profiles, and optional GitHub Actions and SQLFluff setup.

## Features

- `src/`-packaged Python CLI built on Typer and Rich
- Interactive or default-driven project generation
- Adapter templates for BigQuery, Snowflake, PostgreSQL, DuckDB, and Databricks
- Optional starter dbt packages, SQLFluff config, and GitHub Actions workflow
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

## Supported Python

- Python 3.11
- Python 3.12
- Python 3.13

## Local Development

```bash
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

1. Update `src/dbt_forge/__init__.py` with the next version.
2. Add release notes to `CHANGELOG.md`.
3. Commit the release changes.
4. Push a tag in the form `vX.Y.Z`.
5. Let GitHub Actions publish the artifact to PyPI via Trusted Publishing.

For a TestPyPI preflight, run the manual `Release` workflow from GitHub Actions.

## Publishing Setup

- Public repo: [maroil/dbt-forge](https://github.com/maroil/dbt-forge)
- Configure GitHub environments named `pypi` and `testpypi`
- Register the GitHub repo as a Trusted Publisher in PyPI and TestPyPI

## License

MIT. See [LICENSE](LICENSE).
