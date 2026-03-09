---
title: dbt project template
description: Learn what a dbt project template should include and how dbt-forge scaffolds a repeatable starting structure.
---

Teams often search for a `dbt project template` when they want a repeatable starting
point instead of rebuilding the same folders, profiles, and setup files by hand.
`dbt-forge` acts as a dbt project scaffold CLI: it generates the core structure,
adapter-aware configuration, starter models, and optional tooling that most teams add
to every new project anyway.

## What a good dbt project template should include

A practical dbt project template should give you enough structure to start shipping
models immediately without locking you into a rigid architecture.

At minimum, the template should cover:

- dbt project configuration with `dbt_project.yml`
- dependency management for the chosen adapter
- a consistent `models/` layout for staging, intermediate, and marts
- warehouse connection profiles that stay out of version control
- package definitions with pinned versions
- starter tests, selectors, and documentation files
- optional CI, linting, and pre-commit setup for team workflows

`dbt-forge` scaffolds that baseline with [`init`](/docs/cli/init/) and then extends the
same project later with [`add`](/docs/cli/add/).

## Why teams use a dbt scaffold instead of copying old repos

Copying an old repository usually drags along warehouse-specific settings, stale
packages, inconsistent naming, and files that nobody still understands. A dedicated
dbt scaffold is safer because it starts from templates with explicit defaults.

`dbt-forge` improves on copy-paste templates by:

- rendering adapter-aware profiles
- tracking generated files for later updates with [`update`](/docs/cli/update/)
- validating the finished project with [`doctor`](/docs/cli/doctor/)
- supporting generated sources from live warehouse metadata via [`add source --from-database`](/docs/cli/add/)

## Typical dbt-forge project template output

After running `dbt-forge init my_project --defaults`, the generated template usually
includes:

- `dbt_project.yml`
- `pyproject.toml`
- `profiles/profiles.yml`
- `packages.yml`
- `selectors.yml`
- `models/staging/`, `models/intermediate/`, and `models/marts/`
- `.dbt-forge.yml` for template update tracking
- optional SQLFluff, CI, pre-commit, and environment config files

Use [Project structure](/docs/project-structure/) for a full breakdown of each file and
directory.

## When to customize the template

The scaffold should be the starting point, not the final architecture. Most teams
customize it after generation to:

- add domain-specific marts
- change package choices
- enable Mesh-specific project boundaries
- add environment-specific macros and CI rules
- remove example content before production use

That is why the recommended flow is:

1. Follow [Getting started](/docs/getting-started/) to install the CLI and generate the initial project.
2. Use [`init`](/docs/cli/init/) to create the first scaffold.
3. Use [`add`](/docs/cli/add/) to extend the project with marts, models, tests, and packages.
4. Run [`doctor`](/docs/cli/doctor/) to validate naming, test coverage, and health checks.

## Next steps

- Read [How to scaffold a dbt project](/docs/guides/how-to-scaffold-a-dbt-project/) for the end-to-end setup flow.
- Review [dbt project best practices](/docs/guides/dbt-project-best-practices/) before standardizing the template across a team.
- Use [dbt Mesh project setup](/docs/guides/dbt-mesh-project-setup/) if you need multiple dbt projects with clear ownership boundaries.
