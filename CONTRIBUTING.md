# Contributing

## Repository layout

- `cli/` contains the Python package, tests, and release metadata.
- `website/` contains the Astro + Starlight site and public docs.

## CLI development setup

```bash
cd cli
uv sync --all-groups
uv run pre-commit install --hook-type commit-msg
```

## CLI commands

```bash
cd cli
uv run ruff check .
uv run pytest
uv build
uvx twine check dist/*
```

## Website commands

```bash
cd website
pnpm install
pnpm dev
pnpm build
```

## Commit messages

- Use Conventional Commits for every commit.
- Accepted prefixes include `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, and `chore:`.
- The repository includes a `commit-msg` hook and a GitHub Actions check to reject non-conforming messages.

## Pull requests

- Keep changes focused and documented.
- Add or update tests for behavioral changes.
- Ensure the relevant CLI or website checks pass locally before opening a PR.

## Release checklist

1. Update `cli/src/dbt_forge/__init__.py`.
2. Update `CHANGELOG.md`.
3. Merge to `main`.
4. Create and push a `vX.Y.Z` tag.
