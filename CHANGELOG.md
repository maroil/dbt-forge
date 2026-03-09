# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added

- Nothing yet.

## [0.4.0] - 2026-03-09

### Added

- `dbt-forge migrate` command — converts legacy SQL scripts into a dbt project. Parses `CREATE TABLE/VIEW` statements, builds a dependency graph, detects sources, assigns models to staging/intermediate/marts layers, and replaces raw table references with `ref()` and `source()`. Generates source YAML, model YAML, and a migration report. Supports `--dry-run` to preview without writing.
- `dbt-forge add source --from-database` flag — introspects a live warehouse to generate source YAML and staging models from real table metadata. Reads connection config from `profiles.yml`, presents interactive schema and table selection, and fetches column names and types. Supports all 8 adapters via optional dependencies (`pip install dbt-forge[snowflake]`, etc.). Use `--target` to select a non-default profile target.
- `dbt-forge init --mesh` flag — scaffolds a dbt Mesh (multi-project) setup with multiple interconnected sub-projects. Each sub-project gets its own `dbt_project.yml`, `dependencies.yml` (for cross-project refs), group definitions, and models with access controls (staging=protected, intermediate=private, marts=public). Public models automatically get `contract: { enforced: true }`. Includes a root `Makefile` for orchestrated builds. Supports a preset layout (staging → transform → marts) or custom sub-project definitions.
- `dbt-forge add project` command — adds a new sub-project to an existing dbt Mesh setup. Detects the mesh root, lists existing sub-projects, and prompts for upstream dependencies. Generates the sub-project with proper `dependencies.yml` wiring.
- `dbt-forge docs generate` command — uses an LLM to generate model and column descriptions for undocumented models. Scans YAML files for missing descriptions, reads the corresponding SQL, sends context to the LLM, and presents results for interactive review (accept/skip). Supports three providers: Claude (Anthropic), OpenAI, and Ollama (local, no extra deps). Preserves existing descriptions. Flags: `--model` (single model), `--provider`, `--yes` (auto-accept), `--delay` (rate limiting).
- `sql_parser` module — regex-based SQL parsing with `CREATE` statement extraction, `FROM`/`JOIN` table reference detection (excluding CTEs), dependency graph construction, topological sort (Kahn's algorithm with cycle handling), layer detection heuristic, and `ref()`/`source()` substitution.
- `introspect` package — `WarehouseIntrospector` abstract base class with 8 adapter implementations (DuckDB, PostgreSQL, Snowflake, BigQuery, Databricks, Redshift, Trino, Spark). Includes `profile_reader` module for parsing `profiles.yml` with `{{ env_var() }}` resolution.
- `mesh` module — `MeshProjectConfig` and `SubProjectConfig` dataclasses, mesh project generation with access control defaults and contract enforcement.
- `llm` package — `LLMProvider` abstraction with `ClaudeProvider`, `OpenAIProvider`, and `OllamaProvider`. Includes prompt engineering for dbt model documentation and JSON response parsing.
- `docs` module — utilities for finding models with missing descriptions, reading model SQL, and updating YAML files with generated descriptions while preserving existing content.
- Optional dependency groups in `pyproject.toml`: `snowflake`, `bigquery`, `postgres`, `duckdb`, `databricks`, `redshift`, `trino`, `spark`, `claude`, `openai`.
- 96 new tests covering all new features (335 total).

## [0.3.1] - 2026-03-08

### Added

- End-to-end integration tests with DuckDB — 32 tests covering the full dbt lifecycle (init, build, add commands, doctor, status, update) against a real database.
- Integration test CI job in GitHub Actions (`integration-test` with DuckDB).
- `pytest-timeout` dev dependency for integration test timeouts.
- `dbt-core`, `dbt-duckdb`, and `duckdb` dev dependencies for integration testing.
- `integration` pytest marker to separate unit and integration test runs.

### Fixed

- `add mart` / `add source` intermediate stub templates now reference correct column names (`amount_usd`, `customer_id`, `created_at`) matching the staging model output.
- `add exposure` template now uses the provided model name in `ref()` instead of a hardcoded `example_model`.
- `add snapshot` template now uses a placeholder `source('your_source', '<name>')` with a guiding comment instead of referencing a non-existent project-name source.
- Unit test template (`test_stg_example.yml`) now uses correct input amounts (cents) and expected output columns/values matching the staging model transformation.
- `add package` registry: version ranges are now proper Python lists instead of string representations, fixing `SemverError` when installing packages.
- Model YAML templates (`_example_source__models.yml.j2`, `__mart__models.yml.j2`, `_example_source__sources.yml.j2`) now use `data_tests:` instead of deprecated `tests:` key (dbt 1.8+).

## [0.3.0] - 2026-03-08

### Added

- `dbt-forge status` command — Rich terminal dashboard showing model counts by layer, test/doc coverage percentages, sources, and installed packages.
- `dbt-forge update` command — re-applies dbt-forge templates to an existing project and shows unified diffs for changed files. Supports `--dry-run` to preview changes without writing. Interactive mode lets you accept or skip each changed file.
- `.dbt-forge.yml` manifest — written during `init`, stores the dbt-forge version, ProjectConfig, and SHA-256 hashes of all generated files. Powers the `update` command.
- `dbt-forge preset validate <file>` command — validates a preset YAML file and reports errors.
- `dbt-forge init --preset <path-or-url>` flag — applies a preset YAML to `init`. Presets define `defaults` (override prompt defaults) and `locked` fields (skip prompts entirely). Supports local files and HTTPS URLs.
- `dbt-forge add test` now supports a third test type: **schema test** (column-level tests in `.yml`). Auto-detects existing columns from schema YAML, prompts for test types per column (unique, not_null, accepted_values, relationships), and generates a `_<model>__tests.yml` file.
- `dbt-forge add model` now auto-detects existing sources from `models/**/*sources*.yml` files. When sources are found, presents a selection list instead of a free-text prompt.
- `dbt-forge add package` now generates package-specific config in `dbt_project.yml`. Packages with a `config` entry (e.g., `elementary`, `dbt-project-evaluator`) automatically add required `vars` to `dbt_project.yml`.
- Generated `README.md` now includes an "Environment configuration" section when `add_env_config` is enabled, documenting the `generate_schema_name` macro and `.env` setup.
- Shared `scanner.py` module extracted from `doctor.py` — reusable functions for finding models, YAML files, sources, packages, and counting models by layer.
- `dbt-forge doctor` command with 10 health checks (naming conventions, schema/test coverage, hardcoded refs, pinned packages, source freshness, orphaned YAML, sqlfluff config, gitignore, disabled models). Includes `--fix` to auto-generate missing schema stubs, `--ci` for non-interactive mode with exit code 1 on failures, and `--check <name>` to run a single check.
- `dbt-forge add pre-commit` scaffolds `.pre-commit-config.yaml`, `.editorconfig`, and `.sqlfluffignore`.
- `dbt-forge add ci [github|gitlab|bitbucket]` scaffolds CI pipeline config post-init. Reuses existing CI templates and auto-detects the adapter from `profiles.yml`.
- `dbt-forge add model <name>` interactively scaffolds a new model with SQL + YAML. Supports layer selection (staging/intermediate/marts), materialization, column definitions with tests, and incremental model templates.
- `dbt-forge add test <model>` scaffolds a data test (custom SQL assertion) or unit test (dbt 1.8+ mock-based YAML).
- `dbt-forge add package <name>` adds a dbt package to `packages.yml` from a curated registry of 20 packages with known-good version ranges. Use `--list` to browse.
- `init` now offers pre-commit hooks config, environment config (`generate_schema_name` macro + `.env.example`), and `CODEOWNERS` generation.
- `.sqlfluffignore` is now generated alongside `.sqlfluff` when SQLFluff is enabled.

## [0.2.0] - 2026-03-08

### Added

- `dbt-forge add snapshot <name>` scaffolds `snapshots/<name>.sql` with a timestamp strategy stub.
- `dbt-forge add seed <name>` scaffolds `seeds/<name>.csv` and `seeds/_<name>__seeds.yml`.
- `dbt-forge add exposure <name>` scaffolds `models/marts/__<name>__exposures.yml`.
- `dbt-forge add macro <name>` scaffolds `macros/<name>.sql` with a macro block stub.
- `init` now offers four optional prompts — snapshot, seed, exposure, and macro — each generating an example file when enabled.
- `seeds/` and `snapshots/` directories no longer contain a `.gitkeep` placeholder when actual files are written into them.

## [0.1.1] - 2026-03-08

- First public alpha release of the `dbt-forge` CLI on PyPI.
- Added `dbt-forge init` to scaffold opinionated dbt projects with adapter-aware profiles,
  starter marts, optional example models, SQLFluff config, and CI templates.
- Added `dbt-forge add mart` and `dbt-forge add source` to extend an existing dbt project
  without overwriting files that are already present.
- Added dry-run previews, generated `.env` / local `profiles/` conventions, selectors,
  starter tests, and companion project documentation.
