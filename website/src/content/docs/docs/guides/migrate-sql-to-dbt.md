---
title: Migrate SQL to dbt
description: Migrate legacy SQL scripts to dbt models with dbt-forge and replace raw dependencies with ref() and source().
---

`Migrate SQL to dbt` is a common search when teams inherit a folder of legacy SQL files
and want to turn them into a maintainable dbt project. `dbt-forge` addresses that with
[`migrate`](/docs/cli/migrate/), which parses SQL scripts, builds dependencies, and
generates dbt models with `ref()` and `source()`.

## What the migration command handles

The migration flow is designed for SQL-first projects that need structure, not just
file relocation.

`dbt-forge migrate`:

- parses `CREATE TABLE` and `CREATE VIEW` statements
- builds a dependency graph across scripts
- rewrites table references into dbt-native `ref()` and `source()`
- assigns models to staging, intermediate, or marts
- generates a migration report

This gives you a starting dbt project rather than a loose copy of old SQL.

## Basic migration workflow

Run the migration against a directory of SQL files:

```bash
dbt-forge migrate ./legacy_sql/
```

Preview the migration before writing files:

```bash
dbt-forge migrate ./legacy_sql/ --dry-run
```

After migration, inspect the generated layout and compare it with [Project structure](/docs/project-structure/).

## When to scaffold before migrating

If you want a clean project scaffold first, start with [`init`](/docs/cli/init/) and
then migrate the legacy SQL into that project. This is useful when you also want:

- adapter-aware profile templates
- standard packages and selectors
- optional CI, linting, and pre-commit setup
- update tracking with [`update`](/docs/cli/update/)

Use [How to scaffold a dbt project](/docs/guides/how-to-scaffold-a-dbt-project/) for the
recommended setup sequence.

## Validate the migrated project

After conversion, run health checks before treating the output as production-ready:

```bash
dbt-forge doctor
dbt-forge status
```

[`doctor`](/docs/cli/doctor/) catches naming, test coverage, freshness, and reference
issues. [`status`](/docs/cli/status/) gives a fast dashboard view of what the migration
produced.

## Limitations to review manually

Migration accelerates the first pass, but teams should still review:

- business logic naming
- source declarations
- test coverage
- model grain and ownership boundaries
- macros or warehouse-specific SQL that cannot be inferred reliably

That review step is where [dbt project best practices](/docs/guides/dbt-project-best-practices/)
helps.

## Next steps

- Start with [Getting started](/docs/getting-started/) if you have not installed the CLI yet.
- Read the full [`migrate`](/docs/cli/migrate/) command reference for supported behavior.
- Use [`add`](/docs/cli/add/) after migration to scaffold tests, sources, CI, and packages that were not part of the original SQL scripts.
