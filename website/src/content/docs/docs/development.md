---
title: Development
description: Work on the dbt-forge monorepo locally.
---

## Repository layout

```text
dbt-forge/
├── cli/
│   ├── pyproject.toml
│   ├── src/dbt_forge/
│   └── tests/
└── website/
    ├── astro.config.mjs
    ├── src/content/docs/
    └── src/pages/
```

## Work on the CLI

```bash
cd cli
uv sync --all-groups
uv run ruff check .
uv run pytest
uv build
uvx twine check dist/*
```

## Work on the website

```bash
cd website
pnpm install
pnpm dev
pnpm build
```

## Release flow

The package release happens from GitHub Actions on `v*` tags. The website is deployed
separately on Vercel and is not a separately versioned release artifact.

1. Update `cli/src/dbt_forge/__init__.py`
2. Update the repository `CHANGELOG.md`
3. Run the release-candidate checks from
   [`RELEASING.md`](https://github.com/maroil/dbt-forge/blob/main/RELEASING.md)
4. Run the manual TestPyPI preflight from the `Release` workflow
5. Commit and merge the release changes
6. Push a `vX.Y.Z` tag

## Release notes

Use
[`RELEASING.md`](https://github.com/maroil/dbt-forge/blob/main/RELEASING.md)
as the release checklist. It records:

- the first-release scope for the CLI package
- verified GitHub prerequisites from local inspection
- manual Trusted Publishing checks for PyPI and TestPyPI
- the local validation and security commands to run before tagging

## Website hosting

The site is intended for Vercel with:

- Root Directory: `website`
- Build Command: `pnpm build`
- Output Directory: `dist`
