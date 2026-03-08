---
title: preset
description: Command reference for validating and using preset files to standardize project scaffolding.
---

Presets let teams encode project standards into a shareable YAML file. Use them with
`dbt-forge init --preset` to enforce adapter choices, package selections, and feature
flags across multiple dbt projects.

## Commands

```bash
# Validate a preset file
dbt-forge preset validate <path-or-url>

# Use a preset during init
dbt-forge init my_project --preset company-standard.yml
```

## Preset format

A preset is a YAML file with three sections:

```yaml
name: "Company Standard"
description: "Standard config for the analytics team"

defaults:
  adapter: "Snowflake"
  marts: ["finance", "marketing", "product"]
  packages: ["dbt-utils", "dbt-expectations", "elementary"]
  add_examples: true
  add_sqlfluff: true
  ci_providers: ["GitHub Actions"]
  add_unit_tests: false
  add_metricflow: false
  add_snapshot: true
  add_seed: false
  add_exposure: true
  add_macro: false
  add_pre_commit: true
  add_env_config: true
  team_owner: "@analytics-team"

locked:
  - adapter
  - add_sqlfluff
  - ci_providers
```

### `name` and `description`

Optional metadata for the preset. Not used during scaffolding but helps identify
the preset when sharing across teams.

### `defaults`

Values that override the default prompt selections during `init`. The user still sees
the prompt and can change the value, unless the field is also listed in `locked`.

### `locked`

Fields listed here skip the interactive prompt entirely and use the value from
`defaults`. Use this to enforce standards that individual users should not change.

Every locked field **must** have a corresponding entry in `defaults`. A locked field
without a default is a validation error.

## Valid fields

These fields can appear in `defaults` and `locked`:

| Field | Type | Description |
|-------|------|-------------|
| `adapter` | string | Warehouse adapter. One of: `BigQuery`, `Snowflake`, `PostgreSQL`, `DuckDB`, `Databricks`, `Redshift`, `Trino`, `Spark` |
| `marts` | list of strings | Mart domains to scaffold (e.g., `["finance", "marketing"]`) |
| `packages` | list of strings | Starter packages from the [curated registry](/docs/cli/add/#add-package) |
| `add_examples` | boolean | Generate example staging models and tests |
| `add_sqlfluff` | boolean | Generate `.sqlfluff` and `.sqlfluffignore` |
| `ci_providers` | list of strings | CI providers. Values: `"GitHub Actions"`, `"GitLab CI"`, `"Bitbucket Pipelines"` |
| `add_unit_tests` | boolean | Generate unit test examples (requires `add_examples`) |
| `add_metricflow` | boolean | Generate MetricFlow semantic model example |
| `add_snapshot` | boolean | Generate example snapshot |
| `add_seed` | boolean | Generate example seed CSV and YAML |
| `add_exposure` | boolean | Generate example exposure YAML |
| `add_macro` | boolean | Generate example macro |
| `add_pre_commit` | boolean | Generate pre-commit hooks and `.editorconfig` |
| `add_env_config` | boolean | Generate `.env.example` and `generate_schema_name.sql` |
| `team_owner` | string | GitHub team or user for `CODEOWNERS` (e.g., `"@analytics-team"`) |

Unknown fields in `defaults` or `locked` cause a validation error.

## `preset validate`

```bash
dbt-forge preset validate company-standard.yml
dbt-forge preset validate https://example.com/presets/standard.yml
```

Checks a preset file for:

- Unknown fields in `defaults` or `locked`
- Locked fields that have no corresponding default value
- Invalid adapter names (must be one of the 8 supported adapters)
- Invalid CI provider names (must be one of the 3 supported providers)

Exits with code 0 if the preset is valid, code 1 if there are errors.

Example output for an invalid preset:

```
Preset validation errors:
  - Unknown field in defaults: 'warehouse'
  - Locked field 'adapter' has no value in defaults
  - Invalid adapter: 'MySQL'
```

## Using presets with `init`

```bash
# Local file
dbt-forge init analytics_core --preset company-standard.yml

# HTTPS URL
dbt-forge init analytics_core --preset https://example.com/presets/standard.yml

# Combined with --defaults (no prompts shown)
dbt-forge init analytics_core --preset company-standard.yml --defaults
```

The `--preset` flag accepts a local file path or an HTTPS URL. The preset is validated
before `init` begins. If validation fails, `init` exits without scaffolding.

### Interactive mode (default)

When used without `--defaults`:
- **Locked fields** are skipped entirely — the preset value is used
- **Default fields** pre-populate the prompt — the user can change them
- **Unset fields** use the normal dbt-forge defaults

### Non-interactive mode (`--defaults`)

When combined with `--defaults`:
- Preset values override the built-in defaults
- No prompts are shown
- Locked fields behave the same as default fields (both are applied without prompting)

## Behavior and limits

- Presets only affect the `init` command. They do not change `add`, `doctor`, or `status` behavior.
- HTTPS URLs are fetched with Python's `urllib`. No authentication is supported.
- The preset file must be valid YAML. Malformed files cause an error before `init` starts.
- Locked fields must have a value in `defaults`. A locked field without a default is a validation error.
- The `project_name` field cannot be set via presets — it is always provided as a CLI argument or prompted.
