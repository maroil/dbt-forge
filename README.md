# dbt-forge

`dbt-forge` is the monorepo for the `dbt-forge` CLI and its companion docs website.

## Public Release Scope

- Shipped artifact: the Python package `dbt-forge`
- Current release target: `0.3.0` alpha
- Supported Python: `3.11`, `3.12`, `3.13`
- Primary commands: `dbt-forge init`, `dbt-forge doctor`, `dbt-forge status`, `dbt-forge update`, and `dbt-forge add` (mart, source, snapshot, seed, exposure, macro, pre-commit, ci, model, test, package)
- Publish path: GitHub Actions publishes the package to PyPI from `v*` tags
- Website role: docs and marketing for the CLI; it is not a separately versioned release
  artifact

## Repository Layout

`dbt-forge` is organized as a small monorepo:

- `cli/` contains the Python package, tests, and release tooling for the `dbt-forge` CLI.
- `website/` contains the public landing page and docs built with Astro + Starlight.

## Install The CLI

```bash
pip install dbt-forge
```

Or with `uv`:

```bash
uv tool install dbt-forge
```

## Usage

### Scaffold a new dbt project

```bash
# Interactive — choose adapter, marts, packages, CI, and optional features
dbt-forge init

# Non-interactive — use opinionated defaults
dbt-forge init my_project --defaults

# Preview what would be generated without writing files
dbt-forge init my_project --defaults --dry-run

# Use a company preset to enforce standards
dbt-forge init my_project --preset company-standard.yml
```

### Add components to an existing project

Run these from inside a dbt project (any directory containing `dbt_project.yml`):

```bash
# Scaffold structural components
dbt-forge add mart finance
dbt-forge add source salesforce
dbt-forge add snapshot orders
dbt-forge add seed dim_country
dbt-forge add exposure weekly_revenue
dbt-forge add macro cents_to_dollars

# Interactive generators
dbt-forge add model users          # prompts for layer, materialization, columns
dbt-forge add test stg_orders      # data test or unit test
dbt-forge add package dbt-utils    # add from curated registry of 20 packages

# Tooling and CI
dbt-forge add ci github            # generate CI pipeline config
dbt-forge add pre-commit           # pre-commit hooks + editorconfig
```

### Check project health

```bash
# Run all 10 checks (naming, test coverage, schema docs, etc.)
dbt-forge doctor

# Auto-generate missing schema YAML stubs
dbt-forge doctor --fix

# CI mode — exits with code 1 on failures
dbt-forge doctor --ci

# Run a single check
dbt-forge doctor --check test-coverage
```

### Project stats dashboard

```bash
# Show model counts, test/doc coverage, sources, and packages
dbt-forge status
```

### Update templates

```bash
# Preview what would change if templates were re-applied
dbt-forge update --dry-run

# Interactively accept/skip each changed file
dbt-forge update
```

### Presets

```bash
# Validate a preset file
dbt-forge preset validate company-standard.yml

# Use a preset during init (local file or HTTPS URL)
dbt-forge init my_project --preset company-standard.yml
```

## CLI development

```bash
cd cli
uv sync --all-groups
uv run ruff check .
uv run pytest -m "not integration"   # unit tests only
uv run pytest -m integration -v      # integration tests (requires dbt + DuckDB)
uv run pytest                        # all tests
uv build
```

## Release assistant

From the repository root:

```bash
python3 scripts/release_assistant.py prepare 0.3.0
python3 scripts/release_assistant.py verify 0.3.0
python3 scripts/release_assistant.py publish 0.3.0 --confirm
```

Use `prepare` to stage release metadata, `verify` on clean `main`, and `publish` only after
manual approval for the TestPyPI checkpoint.

## Website development

```bash
cd website
pnpm install
pnpm dev
pnpm build
```

## Deployment

The site is designed for Vercel:

- Root Directory: `website`
- Build Command: `pnpm build`
- Output Directory: `dist`

The Python package releases from GitHub Actions on `v*` tags. The website deployment is
separate from the package release.

## Repository links

- GitHub: [maroil/dbt-forge](https://github.com/maroil/dbt-forge)
- Package README: [cli/README.md](cli/README.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Release checklist: [RELEASING.md](RELEASING.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
