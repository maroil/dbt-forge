# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

- No unreleased changes yet.

## [0.1.0] - 2026-03-08

- First public alpha release of the `dbt-forge` CLI on PyPI.
- Added `dbt-forge init` to scaffold opinionated dbt projects with adapter-aware profiles,
  starter marts, optional example models, SQLFluff config, and CI templates.
- Added `dbt-forge add mart` and `dbt-forge add source` to extend an existing dbt project
  without overwriting files that are already present.
- Added dry-run previews, generated `.env` / local `profiles/` conventions, selectors,
  starter tests, and companion project documentation.
