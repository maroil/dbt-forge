# Contributing

## Repository layout

- `cli/` contains the Python package, tests, and release metadata.
- `website/` contains the Astro + Starlight site and public docs.

### Key modules in `cli/src/dbt_forge/`

- `main.py` — Typer app with top-level commands: `init`, `doctor`, `status`, `update`, `migrate`, `docs`, `preset`
- `cli/add.py` — all `add` subcommands (mart, source, model, test, package, project, etc.)
- `cli/migrate.py` — legacy SQL migration command
- `cli/docs_cmd.py` — AI-assisted documentation generation command
- `cli/doctor.py` — project health checks
- `cli/status.py` — project stats dashboard
- `cli/update.py` — template update lifecycle
- `sql_parser.py` — regex-based SQL parsing, dependency graph, topological sort
- `mesh.py` — dbt Mesh multi-project scaffolding
- `docs.py` — model documentation scanning and YAML update utilities
- `introspect/` — warehouse introspection (abstract base, 8 adapter connectors, profile reader)
- `llm/` — LLM provider abstraction (Claude, OpenAI, Ollama)
- `scanner.py` — shared project scanning utilities (models, sources, packages)
- `manifest.py` — `.dbt-forge.yml` manifest for update tracking
- `presets.py` — preset loading, validation, and application
- `prompts/questions.py` — interactive prompts and `ProjectConfig` dataclass
- `generator/project.py` — file generation orchestrator
- `generator/renderer.py` — Jinja2 template rendering

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
uv run pytest -m "not integration"   # unit tests only
uv run pytest -m integration -v      # integration tests (dbt + DuckDB)
uv run pytest                        # all tests
uv build
uvx twine check dist/*
```

### Test structure

- **Unit tests** (`tests/test_*.py`, excluding `test_e2e_duckdb.py`) — fast, no external dependencies, validate file generation and CLI output.
- **Integration tests** (`tests/test_e2e_duckdb.py`, marked `@pytest.mark.integration`) — scaffold a real dbt project, seed DuckDB, and run `dbt build` commands end-to-end.
- **Shared fixtures** (`tests/conftest.py`) — session-scoped `e2e_project_dir` fixture and `run_dbt`/`run_forge` subprocess helpers.

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
python3 scripts/release_assistant.py prepare 0.4.0
python3 scripts/release_assistant.py verify 0.4.0
python3 scripts/release_assistant.py publish 0.4.0 --confirm
```

`prepare` updates release metadata, `verify` is the clean-`main` gate, and `publish` handles the
manual TestPyPI checkpoint before creating the tag and GitHub Release.
