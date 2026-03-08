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

The package release still happens from GitHub Actions on `v*` tags.

1. Update `cli/src/dbt_forge/__init__.py`
2. Update the repository `CHANGELOG.md`
3. Commit and merge the release changes
4. Push a `vX.Y.Z` tag

## Website hosting

The site is intended for Vercel with:

- Root Directory: `website`
- Build Command: `pnpm build`
- Output Directory: `dist`
