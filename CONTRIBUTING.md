# Contributing

## Development setup

```bash
uv sync --all-groups
uv run pre-commit install --hook-type commit-msg
```

## Useful commands

```bash
uv run ruff check .
uv run pytest
uv build
uvx twine check dist/*
```

## Commit messages

- Use Conventional Commits for every commit.
- Accepted prefixes include `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, and `chore:`.
- The repository includes a `commit-msg` hook and a GitHub Actions check to reject non-conforming messages.

## Pull requests

- Keep changes focused and documented.
- Add or update tests for behavioral changes.
- Ensure lint, tests, build, and `twine check` pass locally before opening a PR.

## Release checklist

1. Update `src/dbt_forge/__init__.py`.
2. Update `CHANGELOG.md`.
3. Merge to `main`.
4. Create and push a `vX.Y.Z` tag.
