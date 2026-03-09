"""Tests for ProjectConfig helpers."""

from dbt_forge.prompts.questions import ProjectConfig, _slugify


def _cfg(adapter: str = "BigQuery") -> ProjectConfig:
    return ProjectConfig(
        project_name="p",
        adapter=adapter,
        marts=[],
        packages=[],
        add_examples=True,
        add_sqlfluff=True,
        ci_providers=["GitHub Actions"],
    )


def test_slugify_basic():
    assert _slugify("My Project") == "my_project"


def test_slugify_special_chars():
    assert _slugify("hello-world!") == "hello_world"


def test_slugify_multiple_underscores():
    assert _slugify("hello  world") == "hello_world"


def test_adapter_key_bigquery():
    assert _cfg("BigQuery").adapter_key == "bigquery"


def test_adapter_key_duckdb():
    assert _cfg("DuckDB").adapter_key == "duckdb"


def test_dbt_adapter_package_bigquery():
    assert _cfg("BigQuery").dbt_adapter_package == "dbt-bigquery"


def test_dbt_adapter_package_snowflake():
    assert _cfg("Snowflake").dbt_adapter_package == "dbt-snowflake"


def test_dbt_adapter_package_postgres():
    assert _cfg("PostgreSQL").dbt_adapter_package == "dbt-postgres"


def test_dbt_adapter_package_redshift():
    assert _cfg("Redshift").dbt_adapter_package == "dbt-redshift"


def test_dbt_adapter_package_trino():
    assert _cfg("Trino").dbt_adapter_package == "dbt-trino"


def test_dbt_adapter_package_spark():
    assert _cfg("Spark").dbt_adapter_package == "dbt-spark"


def test_ci_provider_properties():
    c = ProjectConfig(
        project_name="p",
        adapter="BigQuery",
        marts=[],
        packages=[],
        add_examples=True,
        add_sqlfluff=True,
        ci_providers=["GitHub Actions", "GitLab CI"],
    )
    assert c.add_github_actions is True
    assert c.add_gitlab_ci is True
    assert c.add_bitbucket_pipelines is False


def test_empty_ci_providers():
    c = ProjectConfig(
        project_name="p",
        adapter="BigQuery",
        marts=[],
        packages=[],
        add_examples=True,
        add_sqlfluff=True,
        ci_providers=[],
    )
    assert c.add_github_actions is False
    assert c.add_gitlab_ci is False
    assert c.add_bitbucket_pipelines is False


def test_new_optional_fields_default_false():
    c = _cfg()
    assert c.add_snapshot is False
    assert c.add_seed is False
    assert c.add_exposure is False
    assert c.add_macro is False


def test_new_optional_fields_can_be_set():
    c = ProjectConfig(
        project_name="p",
        adapter="BigQuery",
        marts=[],
        packages=[],
        add_examples=True,
        add_sqlfluff=True,
        ci_providers=[],
        add_snapshot=True,
        add_seed=True,
        add_exposure=True,
        add_macro=True,
    )
    assert c.add_snapshot is True
    assert c.add_seed is True
    assert c.add_exposure is True
    assert c.add_macro is True
