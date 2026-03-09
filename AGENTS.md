# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## Repository Layout

- `cli/` - Python package (published to PyPI as `dbt-forge`)
- `website/` - Astro + Starlight documentation site (separate from CLI)

All CLI development happens inside `cli/`.

## Common Commands

```bash
cd cli
uv sync --all-groups                    # install all deps
uv run ruff check .                     # lint (E, F, I rules; 100-char lines)
uv run pytest -m "not integration"      # unit tests (~205 tests, fast)
uv run pytest -m integration -v         # integration tests (requires dbt + DuckDB)
uv run pytest tests/test_doctor.py::TestNamingConventions::test_passes  # single test
uv build && uvx twine check dist/*      # build + validate
```

Commit messages must follow Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, `chore:`). A `commit-msg` hook enforces this.

## Architecture

**Entry point:** `cli/src/dbt_forge/main.py` - Typer app exposing `init`, `add`, `doctor`, `status`, `update`, `migrate`, `docs`, `preset validate` commands.

**Core flow for `init`:**
1. `prompts/questions.py` - `gather_config()` builds a `ProjectConfig` dataclass (single source of truth for all config)
2. `generator/project.py` - `generate_project(config)` orchestrates file creation, conditionally writing files based on config flags
3. `generator/renderer.py` - `render_template()` renders `.j2` templates with Jinja2 (`StrictUndefined`, `trim_blocks`, `lstrip_blocks`)

**`add` subcommands** (`cli/add.py`): 13 post-init scaffolding commands. Each finds the project root via `_find_project_root()` (walks up to `dbt_project.yml`), renders a template, and writes it. Includes `add source --from-database` for warehouse introspection and `add project` for mesh sub-projects.

**`doctor`** (`cli/doctor.py`): 10 health checks on existing dbt projects. Supports `--fix` (auto-gen stubs), `--ci` (exit 1 on fail), `--check <name>`.

**`status`** (`cli/status.py`): Rich dashboard using `scanner.py` utilities.

**`update`** (`cli/update.py`): Re-applies templates by comparing hashes in `.dbt-forge.yml` manifest (`manifest.py`).

**`migrate`** (`cli/migrate.py`): Converts legacy SQL scripts into a dbt project. Uses `sql_parser.py` for regex-based SQL parsing, dependency graph construction, and `ref()`/`source()` substitution.

**`docs generate`** (`cli/docs_cmd.py`): AI-assisted documentation using `llm/` providers (Claude, OpenAI, Ollama). Uses `docs.py` for YAML scanning and update.

**`init --mesh`**: Multi-project dbt Mesh scaffolding via `mesh.py`. Generates interconnected sub-projects with access controls, contracts, and cross-project dependencies.

**`introspect/`**: Warehouse introspection package with abstract `WarehouseIntrospector`, 8 adapter connectors, and `profile_reader` for `profiles.yml` parsing.

**`presets.py`**: Load/validate/apply preset YAML files (local or HTTPS) that pre-configure `ProjectConfig`.

## Jinja2 Escaping for dbt Tags

dbt block tags (`{% snapshot %}`, `{% macro %}`) conflict with Jinja2. Escape them in templates:

```jinja2
{# Variable parts: #}
{{ '{%' }} snapshot {{ name }} {{ '%}' }}

{# Static dbt expressions: #}
{% raw %}{{ hardcoded_ref }}{% endraw %}

{# dbt double-braces: #}
{{ '{{' }} var_name {{ '}}' }}
```

## Test Structure

- **Unit tests:** `cli/tests/test_*.py` (except `test_e2e_duckdb.py`) - no external deps, test file generation, CLI output, config parsing
- **Integration tests:** `cli/tests/test_e2e_duckdb.py` (`@pytest.mark.integration`) - scaffolds real project, seeds DuckDB, runs `dbt build`
- **Shared fixtures:** `cli/tests/conftest.py` - `e2e_project_dir` (session-scoped), `run_dbt()`, `run_forge()` helpers

Test pattern for file generation:
```python
def test_feature():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ProjectConfig(project_name="test", adapter="DuckDB", marts=["finance"],
                               packages=[], add_examples=True, add_sqlfluff=False,
                               ci_providers=[], output_dir=tmpdir)
        generate_project(config)
        assert (Path(tmpdir) / "test" / "dbt_project.yml").exists()
```

## Key Conventions

- All imports use absolute paths: `from dbt_forge.generator.project import generate_project`
- `ProjectConfig` flows through everything: prompts build it, generator consumes it, manifest serializes it, presets override it
- Templates live in `cli/src/dbt_forge/templates/`; adapter profiles in `templates/profiles/`
- Python 3.11+ required; ruff for linting (target py311)
- Build backend: hatchling; version sourced from `src/dbt_forge/__init__.py`
