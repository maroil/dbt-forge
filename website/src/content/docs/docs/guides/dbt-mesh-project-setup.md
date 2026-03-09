---
title: dbt Mesh project setup
description: Set up a dbt Mesh project with dbt-forge when multiple teams need separate dbt projects, interfaces, and ownership.
---

`dbt Mesh project setup` becomes relevant when one monolithic dbt project is no longer a
good fit for ownership or delivery. `dbt-forge` supports this with the `--mesh` flow in
[`init`](/docs/cli/init/), which scaffolds multiple related dbt projects with contracts
and cross-project dependencies in mind.

## When to choose dbt Mesh

Mesh is usually worth the overhead when:

- multiple teams own different business domains
- release cycles need to be decoupled
- access controls differ by project
- cross-project interfaces need to be explicit

If a single team owns everything, start with [How to scaffold a dbt project](/docs/guides/how-to-scaffold-a-dbt-project/)
instead.

## Scaffolding a Mesh setup

Use the mesh flow during initialization:

```bash
dbt-forge init analytics_mesh --mesh
```

This generates a starting structure for multiple dbt projects rather than one shared
project tree. The generated setup is intended to create ownership boundaries early,
before teams accumulate ad hoc dependencies.

## What to review after generation

Even with scaffolded Mesh support, teams should still review:

- project boundaries and naming
- access rules
- contract expectations
- cross-project dependency flow
- CI and release ownership

That review is easier when the initial projects were generated from a consistent template
instead of assembled manually.

## Supporting commands after setup

Once the mesh scaffold exists, you can keep extending it with:

- [`add project`](/docs/cli/add/) for new sub-projects
- [`doctor`](/docs/cli/doctor/) for health checks inside each dbt project
- [`update`](/docs/cli/update/) for template refreshes as dbt-forge evolves

If you are also converting legacy SQL into one of the projects, use [Migrate SQL to dbt](/docs/guides/migrate-sql-to-dbt/).

## Next steps

- Start with [Getting started](/docs/getting-started/) if you have not installed the CLI yet.
- Read [dbt project best practices](/docs/guides/dbt-project-best-practices/) before defining team-wide standards.
- Use [Project structure](/docs/project-structure/) to compare single-project and multi-project layouts.
