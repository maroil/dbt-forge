---
title: dbt project best practices
description: Use dbt-forge to standardize dbt project structure, naming, testing, packages, and health checks.
---

Teams searching for `dbt project best practices` usually want a structure that is easy
to scale, review, and maintain. `dbt-forge` helps by scaffolding a consistent starting
point and enforcing project health checks with [`doctor`](/docs/cli/doctor/).

## 1. Use a consistent project structure

A maintainable dbt project should separate staging, intermediate, and marts so the
purpose of each model is obvious. That is the default structure in `dbt-forge`.

Use [Project structure](/docs/project-structure/) to review the generated layout, then
adapt it carefully rather than mixing every model into one directory.

## 2. Standardize naming conventions

The scaffold uses prefixes like `stg_` and `int_` to make layer boundaries visible.
That improves review speed and reduces naming collisions as the project grows.

Run [`doctor`](/docs/cli/doctor/) regularly to validate naming conventions and other
rules that drift over time.

## 3. Pin packages and manage dependencies explicitly

A dbt project template should define packages intentionally instead of inheriting them
from an older repository. `dbt-forge` generates `packages.yml` with pinned version
ranges and keeps the result updateable through [`update`](/docs/cli/update/).

## 4. Add tests and docs early

Do not treat tests and documentation as a later cleanup step. Teams move faster when:

- source YAML is present
- schema tests are added with the model
- descriptions are written alongside the SQL
- health checks run before pull requests are merged

Use [`add`](/docs/cli/add/) to generate tests and supporting files. Use
[`docs generate`](/docs/cli/docs/) when you want AI-assisted descriptions for existing
models and columns.

## 5. Validate health continuously

The fastest way to lose consistency is to scaffold well once and never check again.
Use these commands as part of the normal workflow:

```bash
dbt-forge doctor
dbt-forge status
```

This gives teams a repeatable way to review structure, coverage, freshness, and project
health.

## 6. Prefer generated standards over manual copy-paste

Copying files from older dbt projects tends to import stale CI config, warehouse
assumptions, and inconsistent ownership. Start from a clean scaffold with
[How to scaffold a dbt project](/docs/guides/how-to-scaffold-a-dbt-project/) or compare
against [dbt project template](/docs/guides/dbt-project-template/).

## Next steps

- Use [Getting started](/docs/getting-started/) if you want the quickest path from install to a valid project.
- Read [`init`](/docs/cli/init/) for the project generation options.
- Use [dbt Mesh project setup](/docs/guides/dbt-mesh-project-setup/) when best practices need to extend across multiple dbt projects.
