# dbt-forge

`dbt-forge` is organized as a small monorepo:

- `cli/` contains the Python package, tests, and release tooling for the `dbt-forge` CLI.
- `website/` contains the public landing page and docs built with Astro + Starlight.

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

The Python package still releases from GitHub Actions on `v*` tags.

## Repository links

- GitHub: [maroil/dbt-forge](https://github.com/maroil/dbt-forge)
- Package README: [cli/README.md](cli/README.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
