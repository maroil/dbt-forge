---
title: How to scaffold a dbt project
description: Scaffold a dbt project with dbt-forge, choose sensible defaults, and extend the project with models, tests, and CI.
---

If you are looking for `how to scaffold a dbt project`, the fastest route is to use a
CLI that creates the project structure, adapter configuration, and starter files in one
pass. `dbt-forge` does that with the [`init`](/docs/cli/init/) command.

## 1. Install the CLI

Install `dbt-forge` with `pip` or `uv`:

```bash
pip install dbt-forge
```

```bash
uv tool install dbt-forge
```

Then verify the CLI is available:

```bash
dbt-forge --help
```

For the full install path, use [Getting started](/docs/getting-started/).

## 2. Generate the initial scaffold

Use defaults when you want a repeatable dbt project scaffold:

```bash
dbt-forge init analytics_core --defaults
```

Use the interactive flow when you want to choose adapters, marts, packages, and
optional tooling:

```bash
dbt-forge init
```

Preview the scaffold without writing files:

```bash
dbt-forge init analytics_core --defaults --dry-run
```

## 3. Review the generated project structure

A useful dbt project scaffold should already contain:

- a `dbt_project.yml`
- dependency configuration for the selected adapter
- `models/staging/`, `models/intermediate/`, and `models/marts/`
- connection profiles in `profiles/profiles.yml`
- package definitions and selectors
- optional linting, CI, and environment files

Use [Project structure](/docs/project-structure/) to inspect what each generated file is
for.

## 4. Run the first dbt commands

After generation, move into the project and install dependencies:

```bash
cd analytics_core
uv sync
uv run --env-file .env dbt deps
uv run --env-file .env dbt debug
```

These commands confirm that the generated project scaffold is valid for local
development.

## 5. Extend the scaffold instead of editing from scratch

Once the base project exists, use [`add`](/docs/cli/add/) instead of manually creating
every file yourself.

Common follow-up commands:

```bash
dbt-forge add mart finance
dbt-forge add model users
dbt-forge add source raw_data --from-database
dbt-forge add ci github
```

This keeps new pieces aligned with the same project structure as the original scaffold.

## 6. Validate the project before the first commit

Use [`doctor`](/docs/cli/doctor/) after scaffolding to catch structural issues early:

```bash
dbt-forge doctor
```

This checks naming conventions, schema coverage, hardcoded references, pinned package
versions, and other best practices.

## When to use Mesh instead of a single project

If one team owns the whole warehouse, a single scaffold is usually enough. If multiple
teams need separate ownership, interfaces, and dependencies, use the Mesh flow:

```bash
dbt-forge init analytics_mesh --mesh
```

Use [dbt Mesh project setup](/docs/guides/dbt-mesh-project-setup/) for the multi-project
case.

## Next steps

- Compare the generated layout with [dbt project template](/docs/guides/dbt-project-template/).
- Use [Migrate SQL to dbt](/docs/guides/migrate-sql-to-dbt/) if you are converting legacy SQL scripts after scaffolding.
- Review [dbt project best practices](/docs/guides/dbt-project-best-practices/) before standardizing the flow across a team.
