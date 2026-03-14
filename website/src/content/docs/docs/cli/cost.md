---
title: cost
description: Command reference for estimating query costs from warehouse usage data.
---

`dbt-forge cost` connects to your data warehouse and estimates the cost of running
each dbt model. Use it to find expensive queries and get materialization suggestions
that reduce warehouse spend.

## Command

```bash
dbt-forge cost [--days N] [--top N] [--report] [--target TARGET] [--format FORMAT]
```

## What it does

The command reads connection credentials from `profiles.yml`, queries warehouse
usage metadata, and shows:

- Top N most expensive models ranked by estimated cost
- Total estimated cost across all models
- Materialization suggestions (e.g., switch a hot view to a table)

## Options

### `--days`

Number of days of usage history to analyze. Defaults to 30.

```bash
dbt-forge cost --days 7
```

### `--top`

Number of top models to display. Defaults to 10.

```bash
dbt-forge cost --top 20
```

### `--report`

Output a markdown report instead of the Rich table. Useful for sharing or saving.

```bash
dbt-forge cost --report
dbt-forge cost --report > cost-report.md
```

### `--target`

dbt profile target to use for the warehouse connection. Defaults to `dev`.

```bash
dbt-forge cost --target prod
```

### `--format`

Output format: `table` (default) or `json`. JSON output includes total cost,
per-model stats, and materialization suggestions.

```bash
dbt-forge cost --format json
```

## Supported warehouses

| Warehouse | Data source | Cost metric |
|-----------|-------------|-------------|
| BigQuery | `INFORMATION_SCHEMA.JOBS` | Bytes billed |
| Snowflake | `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` | Credits used |
| Databricks | `system.billing.usage` | DBUs consumed |

Other adapters (PostgreSQL, DuckDB, Redshift, Trino, Spark) are not yet supported
for cost estimation. The command will show a message and exit.

## Materialization suggestions

The command analyzes query patterns and suggests materialization changes:

| Current | Condition | Suggested | Reason |
|---------|-----------|-----------|--------|
| `view` | Queried 50+ times | `table` | High query count indicates the view is recomputed frequently |
| `table` | Scans 10+ GB | `incremental` | Large full-table rebuilds can be replaced with incremental loads |
| `table` | Queried fewer than 3 times | `view` | Rarely queried tables waste storage and rebuild time |

## Output

### Table view (default)

```
                    dbt-forge cost (last 30 days)
 Model              Bytes Scanned   Exec Count   Est. Cost   Materialization
 fct_orders         12.4 GB         45           $3.20       table
 stg_payments       8.1 GB          120          $2.10       view
 rpt_revenue        5.3 GB          30           $1.40       table

 Total estimated cost: $6.70

 Materialization suggestions:
  stg_payments: view → table (queried 120 times)
```

## Behavior and limits

- Must run from inside an existing dbt project (walks up to find `dbt_project.yml`).
- Reads connection credentials from `profiles.yml` using the `introspect` module.
- Requires appropriate warehouse permissions to query usage metadata tables.
- Cost estimates are approximations based on usage data, not exact billing figures.
- BigQuery cost is estimated at $5/TB scanned (on-demand pricing).
- The command does not modify any warehouse data or dbt project files.
