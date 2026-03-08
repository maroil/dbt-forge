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

## Website copy

- Use [`website/EDITORIAL_GUIDE.md`](website/EDITORIAL_GUIDE.md) as the source of truth for homepage and docs copy.
- Keep public descriptions literal and tied to real commands, files, or generated output.

## Commit messages

- Use Conventional Commits for every commit.
- Accepted prefixes include `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, and `chore:`.
- The repository includes a `commit-msg` hook and a GitHub Actions check to reject non-conforming messages.

## Pull requests

- Keep changes focused and documented.
- Add or update tests for behavioral changes.
- Ensure the relevant CLI or website checks pass locally before opening a PR.

## Release checklist

```bash
python3 scripts/release_assistant.py prepare 0.2.0
python3 scripts/release_assistant.py verify 0.2.0
python3 scripts/release_assistant.py publish 0.2.0 --confirm
```

`prepare` updates release metadata, `verify` is the clean-`main` gate, and `publish` handles the
manual TestPyPI checkpoint before creating the tag and GitHub Release.
