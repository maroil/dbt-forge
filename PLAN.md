# dbt-forge — Feature Roadmap

> Long-term roadmap for dbt-forge features, organized by phase.
> Features marked with checkboxes track implementation status.

---

## Phase 1: Quick Wins

### 1.1 Pre-commit + Linting Scaffolding

SQLFluff + dbt pre-commit integration is one of the top 3 dbt pain points. The `.sqlfluff` config alone isn't enough — teams need a full `.pre-commit-config.yaml` with properly configured hooks, a `.sqlfluffignore` to exclude build artifacts, and an `.editorconfig` for consistent formatting across editors and IDEs.

**Scope:**
- Add `add_pre_commit: bool` prompt to `gather_config()` (default True when sqlfluff enabled)
- New template `.pre-commit-config.yaml.j2` with hooks: sqlfluff-lint, sqlfluff-fix, yamllint, check-yaml, trailing-whitespace, end-of-file-fixer, check-added-large-files
- New template `.sqlfluffignore.j2` excluding target/, dbt_packages/, logs/
- New template `.editorconfig.j2` with 2-space YAML/SQL indent, UTF-8, LF line endings
- New subcommand `dbt-forge add pre-commit` for post-init use
- Update `generator/project.py` to conditionally render these files

**Checklist:**
- [x] Add `add_pre_commit` field to `ProjectConfig`
- [x] Add prompt to `gather_config()`
- [x] Create `.pre-commit-config.yaml.j2` template
- [x] Create `.sqlfluffignore.j2` template
- [x] Create `.editorconfig.j2` template
- [x] Wire up in `generator/project.py`
- [x] Add `add pre-commit` subcommand in `cli/add.py`
- [x] Add tests for new templates and command
- [x] Update existing tests for new prompt

---

### 1.2 `dbt-forge add ci` — Post-init CI Pipeline Generator

Teams that didn't select CI during `init`, or need to add another provider later (e.g., migrating from GitHub to GitLab), have no easy way to generate CI config after project creation. The templates already exist — this just wires them up as a standalone `add` subcommand.

**Scope:**
- `dbt-forge add ci` with interactive prompt: GitHub Actions / GitLab CI / Bitbucket Pipelines
- Reuse existing CI templates (`.github/workflows/dbt_ci.yml.j2`, `.gitlab-ci.yml.j2`, `bitbucket-pipelines.yml.j2`)
- Detect if CI config already exists and prompt before overwriting
- Read adapter from `dbt_project.yml` or profiles to set correct CI config

**Checklist:**
- [x] Add `add ci` subcommand in `cli/add.py`
- [x] Add CI provider prompt (reuse from init)
- [x] Wire up existing CI templates for standalone generation
- [x] Add overwrite detection and warning
- [x] Add tests for `add ci` command

---

### 1.3 Environment Configuration Scaffolding

Dev/staging/prod environment setup is universally confusing for dbt teams. The `generate_schema_name` macro is needed by virtually every production project but isn't included in `dbt init`. Environment variable conventions vary by adapter with no standard documentation.

**Scope:**
- New template `macros/generate_schema_name.sql.j2` — the standard override macro that uses target schema in dev and custom schema in prod
- New template `.env.example.j2` — adapter-specific env vars with comments explaining each one
- Add env var documentation section to generated `README.md`
- New prompt: `add_env_config: bool` (default True)

**Checklist:**
- [x] Create `macros/generate_schema_name.sql.j2` template
- [x] Create `.env.example.j2` template (adapter-aware)
- [x] Update `README.md.j2` with environment setup section
- [x] Add `add_env_config` field and prompt
- [x] Wire up in `generator/project.py`
- [x] Add tests

---

### 1.4 CODEOWNERS + Collaboration Files

Large dbt teams struggle with unclear ownership of model directories and merge conflicts in shared YAML files. A `CODEOWNERS` file maps directories to team owners, enabling auto-assignment of PR reviewers.

**Scope:**
- Optional `CODEOWNERS` file generation with mart-based ownership mapping
- Prompt for team/org name prefix

**Checklist:**
- [x] Create `CODEOWNERS.j2` template
- [x] Add prompt for team ownership
- [x] Wire up in `generator/project.py`
- [x] Add tests

---

## Phase 2: Daily-Use Features

### 2.1 `dbt-forge doctor` — Project Health Check

Teams have no automated way to validate whether their dbt project follows best practices. Common issues go unnoticed until they cause production failures: undocumented models, missing tests, naming convention violations, hardcoded references.

**Scope:**
- New `dbt-forge doctor` command that scans an existing dbt project
- **Checks:**
  - Model naming conventions: staging models prefixed `stg_`, intermediates `int_`, marts use `fct_`/`dim_`/`mrt_`
  - Schema coverage: every `.sql` model has a corresponding `.yml` entry
  - Test coverage: every model has at least one test defined
  - No hardcoded database/schema references in model SQL (e.g., `my_database.my_schema.table`)
  - packages.yml uses pinned version ranges (not floating)
  - Sources have `loaded_at_field` and `freshness` config
  - No orphaned .yml entries referencing non-existent model files
  - .sqlfluff config exists
  - .gitignore includes target/, dbt_packages/, logs/
  - No disabled models (disabled models are tech debt)
- Output: Rich table with pass/fail per check + actionable fix suggestions
- `--fix` flag: auto-generate missing schema.yml stubs for undocumented models
- `--ci` flag: non-interactive, returns exit code 1 on failures (for CI pipelines)
- `--check <name>` flag: run a specific check only

**Checklist:**
- [x] Create `cli/doctor.py` module
- [x] Implement project scanning (find all models, sources, tests, yml files)
- [x] Implement naming convention check
- [x] Implement schema coverage check
- [x] Implement test coverage check
- [x] Implement hardcoded reference detection
- [x] Implement packages.yml version check
- [x] Implement source freshness check
- [x] Implement orphaned yml check
- [x] Implement sqlfluff/gitignore checks
- [x] Add Rich table output formatting
- [x] Add `--fix` flag for auto-generating schema stubs
- [x] Add `--ci` flag for non-interactive mode
- [x] Register `doctor` command in `main.py`
- [x] Add comprehensive tests

---

### 2.2 `dbt-forge add model` — Interactive Model Generator

YAML boilerplate is the most tedious part of dbt development (dbt GitHub issue #1082, filed in 2018). Creating a new model requires creating a SQL file in the right directory, adding a schema.yml entry with column definitions, and adding tests — all manually. This generator automates the entire flow.

**Scope:**
- `dbt-forge add model <name>` with interactive prompts:
  - **Layer**: staging / intermediate / marts (determines directory and prefix)
  - **Materialization**: view / table / incremental / ephemeral (smart defaults per layer)
  - **Source**: for staging models, which source to reference
  - **Columns**: interactive loop — add column name, type, description, then select tests (unique, not_null, accepted_values, relationships)
  - **Description**: model-level description
- Generates:
  - SQL file with correct naming (`stg_`, `int_`, or mart name) in the right directory
  - `.yml` file entry with columns, descriptions, tests, and materialization config
  - For incremental models: includes `is_incremental()` block template
- Smart defaults: staging → view, intermediate → ephemeral, marts → table
- Auto-detects existing sources for the source prompt

**Checklist:**
- [x] Create `add/model.sql.j2` template (with incremental variant)
- [x] Create `add/model.yml.j2` template
- [x] Add model layer/materialization prompts
- [x] Add interactive column definition loop
- [x] Add test selection per column
- [x] Implement directory placement logic
- [x] Implement source auto-detection
- [x] Add `add model` subcommand in `cli/add.py`
- [x] Add tests

---

### 2.3 `dbt-forge add test` — Test Generator

Unit test adoption in dbt is extremely low (~1% column coverage is typical). Teams are confused about the difference between schema tests, data tests, and unit tests. This generator makes it easy to add any type of test.

**Scope:**
- `dbt-forge add test <model_name>` with prompts:
  - **Test type**: schema test (in .yml) / data test (custom SQL) / unit test (dbt 1.8+)
  - **Schema tests**: select columns + test types (unique, not_null, accepted_values, relationships)
  - **Data tests**: generate a custom SQL test file with the model ref'd
  - **Unit tests**: generate a dbt 1.8+ unit test YAML with mock input rows and expected output
- Detects existing model columns from schema.yml if available

**Checklist:**
- [x] Create `add/test_data.sql.j2` template
- [x] Create `add/test_unit.yml.j2` template
- [x] Add test type prompt
- [x] Implement schema test column/type selection
- [x] Implement data test stub generation
- [x] Implement unit test mock generation
- [x] Add `add test` subcommand in `cli/add.py`
- [x] Add tests

---

### 2.4 `dbt-forge add package` — Smart Package Installer

Adding dbt packages requires editing `packages.yml`, knowing compatible versions, and sometimes adding configuration to `dbt_project.yml`. Version conflicts between packages are a frequent source of frustration.

**Scope:**
- `dbt-forge add package <name>` or interactive selection from curated list
- Curated registry of 20+ popular dbt packages with known-good version ranges:
  - dbt-utils, dbt-expectations, dbt-codegen, elementary, dbt-audit-helper, dbt-project-evaluator, dbt-meta-testing, dbt-profiler, metrics, dbt-date, re_data, etc.
- Auto-appends to existing `packages.yml` (parses YAML, adds entry, writes back)
- For packages needing config (e.g., elementary needs schema var, dbt_project_evaluator needs disabled models), auto-generates the config
- Warns on known version conflicts
- `dbt-forge add package --list` to browse available packages

**Checklist:**
- [x] Create package registry data structure (name, hub URL, version range, config needed)
- [x] Populate registry with 20+ packages
- [x] Implement `packages.yml` parser and updater
- [x] Implement config generation for packages that need it
- [x] Add interactive package browser
- [x] Add `add package` subcommand in `cli/add.py`
- [x] Add tests

---

## Phase 3: Power Features

### 3.1 `dbt-forge update` — Template Lifecycle Management

When dbt-forge templates improve (new best practices, security fixes, dbt version updates), existing projects are stuck with the version they were generated with. Copier solves this with template updates — dbt-forge should too.

**Scope:**
- During `init`, write `.dbt-forge.yml` manifest: dbt-forge version, template version hash, all ProjectConfig options used
- `dbt-forge update` command: re-renders templates with stored config, shows unified diff per file
- Interactive per-file: accept / reject / view diff
- Skip files that user has heavily modified (configurable threshold)
- `--dry-run` to preview changes without applying

**Checklist:**
- [x] Design `.dbt-forge.yml` manifest schema
- [x] Write manifest during `init`
- [x] Implement template re-rendering with stored config
- [x] Implement diff generation and display
- [x] Implement per-file accept/reject flow
- [x] Add `update` command in `main.py`
- [x] Add tests

---

### 3.2 Custom Presets / Company Templates

Enterprise teams managing dozens of dbt projects need to enforce standards: same adapter, same packages, same CI provider, same linting rules. A preset system lets them encode standards into a shareable config file.

**Scope:**
- `dbt-forge init --preset <path-or-url>` flag
- Preset = YAML file with pre-filled ProjectConfig values + optional template overrides
- Presets can lock certain options (skip those prompts) or set defaults (still promptable)
- Support local file paths and HTTPS URLs
- `dbt-forge preset validate <file>` to check preset syntax

**Checklist:**
- [x] Design preset YAML schema
- [x] Implement preset loader (local + URL)
- [x] Merge preset values into ProjectConfig
- [x] Support locked vs default-only options
- [x] Add `--preset` flag to `init`
- [x] Add `preset validate` command
- [x] Add tests

---

### 3.3 `dbt-forge add source --from-database` — Warehouse Introspection

Manually writing source definitions for dozens of tables is tedious and error-prone. dbt-coves does introspection but requires their full platform. dbt-codegen does it as a dbt macro (requires running dbt, which requires a working project). A CLI-native solution would be much more accessible.

**Scope:**
- `--from-database` flag on `add source`
- Connects to warehouse using profiles.yml credentials
- Adapter-specific information_schema queries for table/column metadata
- Interactive table selection (checkbox prompt)
- Generates: `_sources.yml` with all selected tables, columns, and data types
- Generates: `stg_` model stubs for each selected table
- Support for all 8 adapters

**Checklist:**
- [ ] Design adapter-specific metadata query interface
- [ ] Implement BigQuery metadata connector
- [ ] Implement Snowflake metadata connector
- [ ] Implement PostgreSQL metadata connector
- [ ] Implement DuckDB metadata connector
- [ ] Implement remaining adapter connectors (Databricks, Redshift, Trino, Spark)
- [ ] Implement profiles.yml credential reader
- [ ] Add interactive table selection
- [ ] Generate sources YAML from metadata
- [ ] Generate staging model stubs
- [ ] Add tests (with mocked connections)

---

### 3.4 `dbt-forge status` — Project Stats Dashboard

There's no quick way to get a high-level overview of a dbt project's health and composition. Teams want to see at a glance: how many models, how well tested, how well documented.

**Scope:**
- Rich terminal dashboard showing:
  - Model count by layer (staging / intermediate / marts / other)
  - Test coverage: % of models with at least one test
  - Documentation coverage: % of columns with descriptions
  - Source freshness coverage: % of sources with freshness config
  - Package list with installed versions
  - Last modified files
- Compact single-screen layout using Rich panels

**Checklist:**
- [x] Create `cli/status.py` module
- [x] Implement model counter and layer classifier
- [x] Implement test coverage calculator
- [x] Implement documentation coverage calculator
- [x] Implement source freshness scanner
- [x] Implement Rich dashboard layout
- [x] Register `status` command in `main.py`
- [x] Add tests

---

## Phase 4: Differentiation

### 4.1 dbt Mesh / Multi-Project Scaffolding

dbt Mesh is the recommended architecture for large-scale dbt deployments, enabling cross-project references with access controls. Setting it up from scratch is complex and poorly documented.

**Scope:**
- `dbt-forge init --mesh` for multi-project structure
- Generates: `dependencies.yml`, model access controls (public/protected/private), group definitions, contract configs
- `dbt-forge add project` — add a sub-project to an existing mesh
- Cross-project `ref()` examples in generated models

**Checklist:**
- [ ] Design mesh project structure
- [ ] Create `dependencies.yml.j2` template
- [ ] Create model templates with access controls
- [ ] Create group definition templates
- [ ] Add `--mesh` flag to `init`
- [ ] Add `add project` subcommand
- [ ] Add tests

---

### 4.2 AI-Assisted Documentation Generation

Column documentation is the most neglected part of dbt projects. Writing descriptions for hundreds of columns is tedious, but undocumented columns make the dbt docs site useless.

**Scope:**
- `dbt-forge docs generate` command
- Reads model SQL logic + column names → generates meaningful descriptions using LLM
- Supports Claude API, OpenAI API, or local models (ollama)
- Outputs to schema.yml files, preserving existing descriptions (only fills blanks)
- Interactive review: accept / edit / reject per description
- `--model <name>` flag to target specific models

**Checklist:**
- [ ] Design LLM provider abstraction (Claude / OpenAI / Ollama)
- [ ] Implement SQL + column context extraction
- [ ] Implement description generation prompts
- [ ] Implement schema.yml reader/writer (preserve existing descriptions)
- [ ] Add interactive review flow
- [ ] Add `docs generate` command
- [ ] Add tests

---

### 4.3 Migration Assistant

Converting legacy SQL projects (stored procedures, scripts, views) to dbt is a massive manual effort that slows dbt adoption. An automated migration assistant would lower the barrier significantly.

**Scope:**
- `dbt-forge migrate <sql-dir>` — scans a directory of `.sql` files
- Detects table references → suggests source definitions
- Identifies `CREATE TABLE/VIEW` statements → converts to dbt models with `ref()` and `source()`
- Detects common patterns (CTEs, temp tables, multi-step transforms) → suggests model splits
- Generates initial project structure with models organized by detected dependencies
- Outputs migration report with manual steps needed

**Checklist:**
- [ ] Implement SQL file scanner
- [ ] Implement table reference parser
- [ ] Implement CREATE statement converter
- [ ] Implement dependency graph builder
- [ ] Implement source definition generator
- [ ] Implement model file generator with ref()/source()
- [ ] Add migration report output
- [ ] Add `migrate` command
- [ ] Add tests

---

### 4.4 Interactive TUI Workbench

A terminal UI provides a visual, interactive way to manage dbt projects without leaving the terminal. More discoverable than remembering CLI flags.

**Scope:**
- `dbt-forge tui` — Textual-based terminal application
- Browse project structure (tree view of models/sources/tests)
- Run doctor checks interactively
- Add models/sources/tests via forms
- DAG visualization (tree view of model dependencies)
- Quick-access to common dbt commands

**Checklist:**
- [ ] Add textual dependency
- [ ] Create TUI app shell
- [ ] Implement project tree browser
- [ ] Implement doctor check panel
- [ ] Implement model/source add forms
- [ ] Implement DAG tree view
- [ ] Add `tui` command
- [ ] Add tests

---

## Phase 5: Ecosystem

### 5.1 Plugin Architecture

Allow the community to extend dbt-forge with custom generators, checks, and templates. Enables domain-specific scaffolding (e.g., Fivetran sources, Airbyte connectors, specific industry data models).

**Scope:**
- Plugin discovery via Python entry points (pip/uv installable)
- Plugin types: generators (new `add` commands), checks (new `doctor` rules), templates (override defaults)
- Plugin API with stable interfaces
- `dbt-forge plugins list` — show installed plugins

**Checklist:**
- [ ] Design plugin API and interfaces
- [ ] Implement entry point discovery
- [ ] Implement plugin loading and registration
- [ ] Add plugin management commands
- [ ] Write plugin development guide
- [ ] Add tests

---

### 5.2 VS Code Extension

A GUI layer on top of dbt-forge for VS Code users. Makes features discoverable through context menus and command palette.

**Scope:**
- VS Code extension wrapping dbt-forge CLI commands
- Right-click context menus: "Add model here", "Add source", "Run doctor"
- Command palette integration
- Inline diagnostics from doctor checks
- Webview panels for status dashboard

**Checklist:**
- [ ] Set up VS Code extension project (TypeScript)
- [ ] Implement command palette commands
- [ ] Implement context menu actions
- [ ] Implement diagnostics provider (from doctor)
- [ ] Implement status webview
- [ ] Publish to VS Code marketplace

---

### 5.3 Template Gallery

A central registry of community-contributed template packs. Teams can share and discover templates for specific use cases (industry-specific models, adapter-specific optimizations).

**Scope:**
- `dbt-forge templates list` — browse available template packs
- `dbt-forge templates install <name>` — install a template pack
- Registry backed by GitHub repository or PyPI
- Template pack format: directory of .j2 files + metadata.yml

**Checklist:**
- [ ] Design template pack format
- [ ] Implement registry client
- [ ] Implement template installer
- [ ] Add template management commands
- [ ] Set up registry repository
- [ ] Add tests
