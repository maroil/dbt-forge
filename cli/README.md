# dbt-forge

`dbt-forge` is a Python CLI for scaffolding opinionated dbt projects with a consistent
layout, starter models, adapter-specific profiles, and optional CI / SQLFluff setup.
The project is currently in its `0.3.x` alpha phase.

## Features

- `src/`-packaged Python CLI built on Typer and Rich
- Interactive or default-driven project generation
- Adapter templates for BigQuery, Snowflake, PostgreSQL, DuckDB, Databricks, Redshift, Trino, and Spark
- 11 `add` subcommands for extending an existing dbt project: mart, source, snapshot, seed, exposure, macro, pre-commit, ci, model, test, package
- `doctor` command with 10 project health checks, `--fix` auto-repair, and `--ci` mode
- `status` command — Rich terminal dashboard showing model counts by layer, test/doc coverage, sources, and packages
- `update` command — re-apply dbt-forge templates with unified diffs and per-file accept/skip
- Custom presets via `--preset` flag — YAML files with defaults and locked fields for team standardization
- `add model` auto-detects existing sources from YAML files for staging layer selection
- `add test` supports schema tests (column-level in `.yml`) in addition to data and unit tests
- `add package` generates package-specific `vars` in `dbt_project.yml` (e.g., elementary, dbt-project-evaluator)
- Optional pre-commit hooks, SQLFluff config, `.editorconfig`, and CI templates
- Environment config scaffolding: `generate_schema_name` macro and adapter-specific `.env.example`
- `CODEOWNERS` file generation with mart-based ownership mapping
- Curated package registry with 20 dbt packages and known-good version ranges
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

Add components inside an existing dbt project:

```bash
dbt-forge add mart finance
dbt-forge add source salesforce
dbt-forge add snapshot orders
dbt-forge add seed dim_country
dbt-forge add exposure weekly_revenue
dbt-forge add macro cents_to_dollars
dbt-forge add pre-commit
dbt-forge add ci github
dbt-forge add model users
dbt-forge add test stg_orders
dbt-forge add package dbt-utils
```

Run health checks on an existing project:

```bash
dbt-forge doctor
dbt-forge doctor --fix
dbt-forge doctor --ci
dbt-forge doctor --check naming-conventions
```

View project stats and update templates:

```bash
dbt-forge status
dbt-forge update --dry-run
dbt-forge update
```

Manage presets:

```bash
dbt-forge preset validate company-standard.yml
dbt-forge init my_project --preset company-standard.yml
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
uv run pytest -m "not integration"   # unit tests only (~205 tests)
uv run pytest -m integration -v      # integration tests with DuckDB (~32 tests)
uv run pytest                        # all tests
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

From the repository root:

```bash
python3 scripts/release_assistant.py prepare 0.3.0
python3 scripts/release_assistant.py verify 0.3.0
python3 scripts/release_assistant.py publish 0.3.0 --confirm
```

`prepare` stages the version and changelog updates. `verify` is the release gate and requires a
clean `main` branch aligned with `origin/main`. `publish` dispatches the TestPyPI preflight,
waits for manual confirmation, then tags and creates the GitHub Release.

For the detailed checklist and publish prerequisites, see
[`RELEASING.md`](https://github.com/maroil/dbt-forge/blob/main/RELEASING.md).

## Publishing Setup

- Public repo: [maroil/dbt-forge](https://github.com/maroil/dbt-forge)
- Configure GitHub environments named `pypi` and `testpypi`
- Register the GitHub repo as a Trusted Publisher in PyPI and TestPyPI

## License

MIT. See [LICENSE](LICENSE).
