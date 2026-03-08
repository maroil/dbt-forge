"""Tests for ProjectConfig helpers."""

from dbt_forge.prompts.questions import ProjectConfig, _slugify


def test_slugify_basic():
    assert _slugify("My Project") == "my_project"


def test_slugify_special_chars():
    assert _slugify("hello-world!") == "hello_world"


def test_slugify_multiple_underscores():
    assert _slugify("hello  world") == "hello_world"


def test_adapter_key_bigquery():
    c = ProjectConfig("p", "BigQuery", [], [], True, True, True)
    assert c.adapter_key == "bigquery"


def test_adapter_key_duckdb():
    c = ProjectConfig("p", "DuckDB", [], [], True, True, True)
    assert c.adapter_key == "duckdb"


def test_dbt_adapter_package_bigquery():
    c = ProjectConfig("p", "BigQuery", [], [], True, True, True)
    assert c.dbt_adapter_package == "dbt-bigquery"


def test_dbt_adapter_package_snowflake():
    c = ProjectConfig("p", "Snowflake", [], [], True, True, True)
    assert c.dbt_adapter_package == "dbt-snowflake"


def test_dbt_adapter_package_postgres():
    c = ProjectConfig("p", "PostgreSQL", [], [], True, True, True)
    assert c.dbt_adapter_package == "dbt-postgres"
