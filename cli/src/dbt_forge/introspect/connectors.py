"""Warehouse connector implementations for each dbt adapter."""

from __future__ import annotations

from dbt_forge.introspect.base import ColumnMetadata, TableMetadata, WarehouseIntrospector


class DuckDBIntrospector(WarehouseIntrospector):
    def __init__(self, path: str = ":memory:", **kwargs):
        self._path = path
        self._conn = None

    def connect(self):
        import duckdb

        self._conn = duckdb.connect(self._path)

    def list_schemas(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"
        ).fetchall()
        return [r[0] for r in rows]

    def list_tables(self, schema: str) -> list[TableMetadata]:
        rows = self._conn.execute(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = ?",
            [schema],
        ).fetchall()
        return [
            TableMetadata(schema_name=schema, table_name=r[0], table_type=r[1]) for r in rows
        ]

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        rows = self._conn.execute(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
            [schema, table],
        ).fetchall()
        return [
            ColumnMetadata(name=r[0], data_type=r[1], is_nullable=r[2] == "YES") for r in rows
        ]

    def close(self):
        if self._conn:
            self._conn.close()


class PostgresIntrospector(WarehouseIntrospector):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "",
        password: str = "",
        dbname: str = "",
        **kwargs,
    ):
        self._config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "dbname": dbname,
        }
        self._conn = None

    def connect(self):
        import psycopg2

        self._conn = psycopg2.connect(**self._config)

    def list_schemas(self) -> list[str]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"
        )
        return [r[0] for r in cur.fetchall()]

    def list_tables(self, schema: str) -> list[TableMetadata]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = %s",
            (schema,),
        )
        return [
            TableMetadata(schema_name=schema, table_name=r[0], table_type=r[1])
            for r in cur.fetchall()
        ]

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            (schema, table),
        )
        return [
            ColumnMetadata(name=r[0], data_type=r[1], is_nullable=r[2] == "YES")
            for r in cur.fetchall()
        ]

    def close(self):
        if self._conn:
            self._conn.close()


class SnowflakeIntrospector(WarehouseIntrospector):
    def __init__(
        self,
        account: str = "",
        user: str = "",
        password: str = "",
        database: str = "",
        warehouse: str = "",
        role: str = "",
        **kwargs,
    ):
        self._config = {
            k: v
            for k, v in {
                "account": account,
                "user": user,
                "password": password,
                "database": database,
                "warehouse": warehouse,
                "role": role,
            }.items()
            if v
        }
        self._conn = None

    def connect(self):
        import snowflake.connector

        self._conn = snowflake.connector.connect(**self._config)

    def list_schemas(self) -> list[str]:
        cur = self._conn.cursor()
        cur.execute("SHOW SCHEMAS")
        return [r[1] for r in cur.fetchall() if r[1] not in ("INFORMATION_SCHEMA",)]

    def list_tables(self, schema: str) -> list[TableMetadata]:
        cur = self._conn.cursor()
        cur.execute(f'SHOW TABLES IN SCHEMA "{schema}"')
        tables = [
            TableMetadata(schema_name=schema, table_name=r[1], table_type="TABLE")
            for r in cur.fetchall()
        ]
        cur.execute(f'SHOW VIEWS IN SCHEMA "{schema}"')
        tables += [
            TableMetadata(schema_name=schema, table_name=r[1], table_type="VIEW")
            for r in cur.fetchall()
        ]
        return tables

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable, comment "
            "FROM information_schema.columns "
            f"WHERE table_schema = '{schema}' AND table_name = '{table}' "
            "ORDER BY ordinal_position"
        )
        return [
            ColumnMetadata(
                name=r[0], data_type=r[1], is_nullable=r[2] == "YES", comment=r[3] or ""
            )
            for r in cur.fetchall()
        ]

    def close(self):
        if self._conn:
            self._conn.close()


class BigQueryIntrospector(WarehouseIntrospector):
    def __init__(self, project: str = "", dataset: str = "", **kwargs):
        self._project = project
        self._client = None

    def connect(self):
        from google.cloud import bigquery

        self._client = bigquery.Client(project=self._project)

    def list_schemas(self) -> list[str]:
        datasets = list(self._client.list_datasets())
        return [d.dataset_id for d in datasets]

    def list_tables(self, schema: str) -> list[TableMetadata]:
        tables = list(self._client.list_tables(f"{self._project}.{schema}"))
        return [
            TableMetadata(schema_name=schema, table_name=t.table_id, table_type=t.table_type)
            for t in tables
        ]

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        ref = self._client.get_table(f"{self._project}.{schema}.{table}")
        return [
            ColumnMetadata(
                name=f.name,
                data_type=f.field_type,
                is_nullable=f.mode != "REQUIRED",
                comment=f.description or "",
            )
            for f in ref.schema
        ]

    def close(self):
        if self._client:
            self._client.close()


class DatabricksIntrospector(WarehouseIntrospector):
    def __init__(
        self,
        server_hostname: str = "",
        http_path: str = "",
        access_token: str = "",
        catalog: str = "",
        **kwargs,
    ):
        self._config = {
            "server_hostname": server_hostname,
            "http_path": http_path,
            "access_token": access_token,
            "catalog": catalog,
        }
        self._conn = None

    def connect(self):
        from databricks import sql

        self._conn = sql.connect(
            server_hostname=self._config["server_hostname"],
            http_path=self._config["http_path"],
            access_token=self._config["access_token"],
        )

    def list_schemas(self) -> list[str]:
        cur = self._conn.cursor()
        catalog = self._config.get("catalog", "hive_metastore")
        cur.execute(f"SHOW SCHEMAS IN {catalog}")
        return [r[0] for r in cur.fetchall() if r[0] not in ("information_schema",)]

    def list_tables(self, schema: str) -> list[TableMetadata]:
        cur = self._conn.cursor()
        cur.execute(f"SHOW TABLES IN {schema}")
        return [
            TableMetadata(schema_name=schema, table_name=r[1], table_type="TABLE")
            for r in cur.fetchall()
        ]

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        cur = self._conn.cursor()
        cur.execute(f"DESCRIBE TABLE {schema}.{table}")
        return [
            ColumnMetadata(name=r[0], data_type=r[1], is_nullable=True, comment=r[2] or "")
            for r in cur.fetchall()
            if not r[0].startswith("#")
        ]

    def close(self):
        if self._conn:
            self._conn.close()


class RedshiftIntrospector(PostgresIntrospector):
    """Redshift uses the same protocol as PostgreSQL."""

    pass


class TrinoIntrospector(WarehouseIntrospector):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        user: str = "",
        catalog: str = "",
        **kwargs,
    ):
        self._config = {"host": host, "port": port, "user": user, "catalog": catalog}
        self._conn = None

    def connect(self):
        import trino

        self._conn = trino.dbapi.connect(
            host=self._config["host"],
            port=self._config["port"],
            user=self._config["user"],
            catalog=self._config["catalog"],
        )

    def list_schemas(self) -> list[str]:
        cur = self._conn.cursor()
        cur.execute("SHOW SCHEMAS")
        return [r[0] for r in cur.fetchall() if r[0] not in ("information_schema",)]

    def list_tables(self, schema: str) -> list[TableMetadata]:
        cur = self._conn.cursor()
        cur.execute(f'SHOW TABLES IN "{schema}"')
        return [
            TableMetadata(schema_name=schema, table_name=r[0], table_type="TABLE")
            for r in cur.fetchall()
        ]

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        cur = self._conn.cursor()
        cur.execute(f'SHOW COLUMNS FROM "{schema}"."{table}"')
        return [ColumnMetadata(name=r[0], data_type=r[1]) for r in cur.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()


class SparkIntrospector(WarehouseIntrospector):
    def __init__(self, host: str = "localhost", port: int = 10000, **kwargs):
        self._config = {"host": host, "port": port}
        self._conn = None

    def connect(self):
        from pyhive import hive

        self._conn = hive.connect(host=self._config["host"], port=self._config["port"])

    def list_schemas(self) -> list[str]:
        cur = self._conn.cursor()
        cur.execute("SHOW DATABASES")
        return [r[0] for r in cur.fetchall() if r[0] != "information_schema"]

    def list_tables(self, schema: str) -> list[TableMetadata]:
        cur = self._conn.cursor()
        cur.execute(f"SHOW TABLES IN {schema}")
        return [
            TableMetadata(schema_name=schema, table_name=r[1], table_type="TABLE")
            for r in cur.fetchall()
        ]

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        cur = self._conn.cursor()
        cur.execute(f"DESCRIBE {schema}.{table}")
        return [
            ColumnMetadata(name=r[0], data_type=r[1], comment=r[2] or "")
            for r in cur.fetchall()
            if r[0] and not r[0].startswith("#")
        ]

    def close(self):
        if self._conn:
            self._conn.close()


ADAPTER_MAP: dict[str, type[WarehouseIntrospector]] = {
    "duckdb": DuckDBIntrospector,
    "postgres": PostgresIntrospector,
    "postgresql": PostgresIntrospector,
    "snowflake": SnowflakeIntrospector,
    "bigquery": BigQueryIntrospector,
    "databricks": DatabricksIntrospector,
    "redshift": RedshiftIntrospector,
    "trino": TrinoIntrospector,
    "spark": SparkIntrospector,
}

ADAPTER_DEPS: dict[str, str] = {
    "duckdb": "duckdb",
    "postgres": "psycopg2-binary",
    "postgresql": "psycopg2-binary",
    "snowflake": "snowflake-connector-python",
    "bigquery": "google-cloud-bigquery",
    "databricks": "databricks-sql-connector",
    "redshift": "psycopg2-binary",
    "trino": "trino",
    "spark": "pyhive",
}


def get_introspector(adapter_key: str, **config) -> WarehouseIntrospector:
    """Factory: return a WarehouseIntrospector for the given adapter key."""
    cls = ADAPTER_MAP.get(adapter_key)
    if cls is None:
        supported = ", ".join(sorted(ADAPTER_MAP.keys()))
        raise ValueError(f"Unsupported adapter: {adapter_key}. Supported: {supported}")
    try:
        return cls(**config)
    except ImportError:
        dep = ADAPTER_DEPS.get(adapter_key, adapter_key)
        raise ImportError(
            f"Missing dependency for {adapter_key}. Install with: pip install {dep}"
        )
