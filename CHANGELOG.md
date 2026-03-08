# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

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
