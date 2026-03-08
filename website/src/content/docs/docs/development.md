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

From the repository root:

```bash
python3 scripts/release_assistant.py prepare 0.2.0
python3 scripts/release_assistant.py verify 0.2.0
python3 scripts/release_assistant.py publish 0.2.0 --confirm
```

`prepare` stages the version and changelog updates. `verify` is the release gate and requires a
clean `main` branch aligned with `origin/main`. `publish` dispatches the manual TestPyPI
preflight first, then pauses for confirmation before creating and pushing the release tag.

## Release notes

Use
[`RELEASING.md`](https://github.com/maroil/dbt-forge/blob/main/RELEASING.md)
as the release checklist. It records:

- the package release scope for the CLI
- verified GitHub prerequisites from local inspection
- manual Trusted Publishing checks for PyPI and TestPyPI
- the release assistant commands and validation gates to run before tagging

## Website hosting

The site is intended for Vercel with:

- Root Directory: `website`
- Build Command: `pnpm build`
- Output Directory: `dist`
