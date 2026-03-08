# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added

- Nothing yet.

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
