"""dbt-forge cost — query cost estimation logic."""

from __future__ import annotations

from dataclasses import dataclass, field

from dbt_forge.introspect.base import WarehouseIntrospector


@dataclass
class QueryStat:
    model_name: str
    total_bytes_scanned: int = 0
    avg_duration_seconds: float = 0.0
    execution_count: int = 0
    estimated_cost_usd: float = 0.0
    materialization: str = ""


@dataclass
class CostReport:
    stats: list[QueryStat] = field(default_factory=list)

    @property
    def total_estimated_cost(self) -> float:
        return sum(s.estimated_cost_usd for s in self.stats)

    def top_n(self, n: int = 10) -> list[QueryStat]:
        """Return top N most expensive models."""
        return sorted(self.stats, key=lambda s: s.estimated_cost_usd, reverse=True)[:n]

    def materialization_suggestions(self) -> list[dict]:
        """Suggest materialization changes based on usage patterns."""
        suggestions = []
        for stat in self.stats:
            if stat.materialization == "view" and stat.execution_count > 50:
                suggestions.append(
                    {
                        "model": stat.model_name,
                        "current": "view",
                        "suggested": "table",
                        "reason": f"High query count ({stat.execution_count})",
                    }
                )
            elif (
                stat.materialization == "table"
                and stat.total_bytes_scanned > 10 * 1024**3
                and stat.execution_count < 5
            ):
                suggestions.append(
                    {
                        "model": stat.model_name,
                        "current": "table",
                        "suggested": "incremental",
                        "reason": "Large table with low query count",
                    }
                )
            elif stat.materialization == "table" and stat.execution_count < 2:
                suggestions.append(
                    {
                        "model": stat.model_name,
                        "current": "table",
                        "suggested": "view",
                        "reason": "Rarely queried",
                    }
                )
        return suggestions


# ---------------------------------------------------------------------------
# Adapter-specific query stat retrieval
# ---------------------------------------------------------------------------


def get_bigquery_stats(introspector: WarehouseIntrospector, days: int) -> list[QueryStat]:
    """Get query stats from BigQuery INFORMATION_SCHEMA.JOBS."""
    client = introspector._client  # type: ignore[attr-defined]
    query = f"""
        SELECT
            REGEXP_EXTRACT(query, r'`[^`]*\\.([^`]+)`') AS model_name,
            SUM(total_bytes_billed) AS total_bytes,
            AVG(TIMESTAMP_DIFF(end_time, start_time, SECOND)) AS avg_duration,
            COUNT(*) AS exec_count,
            SUM(total_bytes_billed) / POW(1024, 4) * 6.25 AS est_cost_usd
        FROM `region-us`.INFORMATION_SCHEMA.JOBS
        WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            AND job_type = 'QUERY'
            AND state = 'DONE'
            AND total_bytes_billed > 0
        GROUP BY model_name
        HAVING model_name IS NOT NULL
        ORDER BY est_cost_usd DESC
    """
    rows = client.query(query).result()
    return [
        QueryStat(
            model_name=row.model_name,
            total_bytes_scanned=row.total_bytes or 0,
            avg_duration_seconds=float(row.avg_duration or 0),
            execution_count=row.exec_count or 0,
            estimated_cost_usd=float(row.est_cost_usd or 0),
        )
        for row in rows
    ]


def get_snowflake_stats(introspector: WarehouseIntrospector, days: int) -> list[QueryStat]:
    """Get query stats from Snowflake QUERY_HISTORY."""
    conn = introspector._conn  # type: ignore[attr-defined]
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            SPLIT_PART(query_tag, '.', -1) AS model_name,
            SUM(bytes_scanned) AS total_bytes,
            AVG(total_elapsed_time / 1000) AS avg_duration,
            COUNT(*) AS exec_count,
            SUM(credits_used_cloud_services) * 3.0 AS est_cost_usd
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE start_time > DATEADD('day', -{days}, CURRENT_TIMESTAMP())
            AND execution_status = 'SUCCESS'
            AND query_type = 'SELECT'
        GROUP BY model_name
        HAVING model_name IS NOT NULL AND model_name != ''
        ORDER BY est_cost_usd DESC
    """)
    return [
        QueryStat(
            model_name=row[0],
            total_bytes_scanned=row[1] or 0,
            avg_duration_seconds=float(row[2] or 0),
            execution_count=row[3] or 0,
            estimated_cost_usd=float(row[4] or 0),
        )
        for row in cur.fetchall()
    ]


def get_databricks_stats(introspector: WarehouseIntrospector, days: int) -> list[QueryStat]:
    """Get query stats from Databricks system tables."""
    conn = introspector._conn  # type: ignore[attr-defined]
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            statement_text,
            SUM(total_duration_ms) / 1000 AS total_duration,
            COUNT(*) AS exec_count
        FROM system.query.history
        WHERE start_time > DATE_SUB(CURRENT_DATE(), {days})
            AND status = 'FINISHED'
        GROUP BY statement_text
        ORDER BY total_duration DESC
        LIMIT 100
    """)
    return [
        QueryStat(
            model_name=row[0][:50] if row[0] else "unknown",
            avg_duration_seconds=float(row[1] or 0),
            execution_count=row[2] or 0,
        )
        for row in cur.fetchall()
    ]


ADAPTER_STATS_FN = {
    "bigquery": get_bigquery_stats,
    "snowflake": get_snowflake_stats,
    "databricks": get_databricks_stats,
}

SUPPORTED_ADAPTERS = list(ADAPTER_STATS_FN.keys())
