---
title: migrate
description: Command reference for converting legacy SQL scripts into a dbt project with ref() and source().
---

`dbt-forge migrate` converts a directory of SQL scripts into a dbt project. It parses
`CREATE TABLE` and `CREATE VIEW` statements, builds a dependency graph, and generates
models with `ref()` and `source()` calls replacing raw table references.

## Command

```bash
dbt-forge migrate SQL_DIR [--output PATH] [--dry-run]
```

## What it does

1. **Scans** the input directory recursively for `.sql` files
2. **Parses** each file for `CREATE TABLE/VIEW` statements and `FROM`/`JOIN` table references
3. **Builds** a dependency graph between files based on which tables they create and reference
4. **Detects sources** — tables referenced but never created in any SQL file
5. **Assigns layers** — staging (depends only on sources), marts (no downstream dependents), intermediate (everything else)
6. **Generates** dbt models with `ref()` and `source()` substituted for raw table names
7. **Writes** source YAML, model YAML, and a migration report

## Arguments

### `SQL_DIR`

Required. Path to a directory containing SQL files to migrate. The command scans
recursively for `.sql` files.

## Options

### `--output`, `-o`

Output directory for the generated dbt models. Defaults to the current directory.
Creates a `migrated_project/` subdirectory with `models/` inside.

### `--dry-run`

Preview the migration plan without writing files. Shows the dependency graph, layer
assignments, and file count.

## SQL parsing

The parser handles these patterns:

- `CREATE TABLE schema.table AS SELECT ...`
- `CREATE OR REPLACE VIEW schema.table AS ...`
- `CREATE TABLE IF NOT EXISTS table (...)`
- `CREATE TEMP TABLE ...`
- `FROM schema.table` and `JOIN schema.table` references
- CTEs (`WITH name AS (...)`) — CTE names are excluded from external references
- Column definitions in `CREATE TABLE name (col1 type1, col2 type2)`

The parser is regex-based and does not require `sqlparse` or any SQL parsing library.

## Layer detection

Each model is assigned to a layer using this heuristic:

| Condition | Assigned layer |
|-----------|----------------|
| Only references sources (tables never created in any file) | `staging` |
| No downstream dependents (no other model references it) | `marts` |
| Everything else | `intermediate` |

## Generated files

```
migrated_project/
├── models/
│   ├── staging/
│   │   └── <source>/
│   │       ├── _<source>__sources.yml    # source YAML
│   │       └── stg_<source>__<table>.sql # staging model
│   ├── intermediate/
│   │   ├── int_<name>.sql                # intermediate model
│   │   └── _int_<name>__models.yml
│   └── marts/
│       ├── <name>.sql                    # mart model
│       └── _<name>__models.yml
└── migration_report.md                   # summary
```

## Migration report

The generated `migration_report.md` includes:

- File count and model summary
- Table of models with layer assignments and original file paths
- Source tables grouped by schema
- Dependency order (topological sort)

## Example

Given two SQL files:

```sql
-- raw_orders.sql
CREATE TABLE analytics.raw_orders AS
SELECT * FROM warehouse.orders;

-- order_summary.sql
CREATE VIEW analytics.order_summary AS
SELECT customer_id, SUM(amount) as total
FROM analytics.raw_orders
GROUP BY customer_id;
```

Running `dbt-forge migrate ./sql/` produces:

- `stg_warehouse__orders.sql` with `{{ source('warehouse', 'orders') }}`
- `int_raw_orders.sql` with `{{ ref('stg_warehouse__orders') }}`
- `order_summary.sql` (marts) with `{{ ref('int_raw_orders') }}`
- Source YAML for `warehouse.orders`

## Behavior and limits

- The parser uses regex, not a full SQL parser. Complex or non-standard SQL may need manual review after migration.
- Temporary tables (`CREATE TEMP TABLE`) are parsed but treated like regular tables in the dependency graph.
- Circular dependencies are handled by breaking one edge in the cycle.
- The command does not connect to any database — it works entirely from SQL file content.
- No new dependencies are required.
