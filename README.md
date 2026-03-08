# dbt-forge

`dbt-forge` is the monorepo for the `dbt-forge` CLI and its companion docs website.

## Public Release Scope

- Shipped artifact: the Python package `dbt-forge`
- Current release target: `0.1.1` alpha
- Supported Python: `3.11`, `3.12`, `3.13`
- Primary commands: `dbt-forge init`, `dbt-forge add mart`, `dbt-forge add source`
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

## CLI development

```bash
cd cli
uv sync --all-groups
uv run ruff check .
uv run pytest
uv build
```

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
