# dbt-forge — Feature Roadmap

> Long-term roadmap for dbt-forge features, organized by phase.
> Phases 1–4.4 are complete. This document covers upcoming work only.
>
> **Current state:** v0.4.1 — 514+ tests, 13 `add` subcommands, 11 doctor checks, 6 lint rules,
> AI docs, mesh support, cost/impact/contracts/changelog all shipped.
> Phase 5.0 (DX quick wins) complete: command grouping, JSON output, remediation hints,
> contract enforcement check, init review screen.

---

## Phase 5.0: Developer Experience Quick Wins ✅

Small, high-value improvements to polish the CLI before adding major new features. **All 5 features complete — 514 tests passing.**

### 5.0.1 Init Summary / Review Screen ✅

Users answer 15+ prompts but can't review choices before files are written. Show a Rich table summarizing all selections with a "Confirm? [Y/n]" before generation.

**Checklist:**
- [x] Add summary table rendering after `gather_config()` in `cli/init.py`
- [x] Add confirmation prompt (skip in `--defaults` and `--dry-run` modes)
- [x] Add tests

### 5.0.2 Smart Doctor Remediation Suggestions ✅

Every `doctor` failure should suggest the exact `dbt-forge` command to fix it (e.g., "Run `dbt-forge add test orders` to add test coverage").

**Checklist:**
- [x] Add remediation message to each of the 11 checks in `cli/doctor.py`
- [x] Display remediation in Rich output (dimmed hint line under each failure)
- [x] Add tests for remediation messages

### 5.0.3 JSON Output for Analysis Commands ✅

Enable CI/CD integrations and dashboards by adding `--format json` to all analysis commands.

**Checklist:**
- [x] Add `--format` option (table/json) to `doctor`, `lint`, `impact`, `cost` (changelog already had it)
- [x] Implement JSON serialization for each command's output (`render_*_json()`)
- [x] Add tests for JSON output format (unit + CLI integration)

### 5.0.4 Command Grouping in Help ✅

Organize 20+ commands into categories so `dbt-forge --help` is scannable.

**Checklist:**
- [x] Group commands in `main.py`: Scaffold (`init`, `add`), Analyze (`doctor`, `lint`, `impact`, `cost`, `status`), Govern (`contracts`, `changelog`), AI (`docs`), Migrate (`migrate`, `update`), Utility (`adapters`, `preset`)
- [x] Use Typer `rich_help_panel` for grouping
- [x] Remove old `HelpGroup` class, add compact `epilog` with getting-started examples
- [x] Add tests

### 5.0.5 Contract Enforcement Doctor Check ✅

New doctor check: "All public/mart models should have `contract: { enforced: true }`."

**Checklist:**
- [x] Add `contract-enforcement` check to `cli/doctor.py` (11th check)
- [x] Scan mart-layer models for missing contract config
- [x] Add `--fix` support (`fix_contract_enforcement()` injects config into YAML)
- [x] Add tests

---

## Phase 5.1: MCP Server & Governance

### 5.1.1 dbt-forge as MCP Server

Expose forge commands (doctor, lint, impact, cost, status) as MCP tools so AI agents (Cursor, Claude Code, Windsurf) can scaffold and analyze dbt projects conversationally.

**Why:** dbt Labs shipped the [dbt MCP server](https://github.com/dbt-labs/dbt-mcp) for querying dbt metadata. dbt-forge should complement it by exposing project scaffolding and analysis as MCP tools — this is the highest-differentiation opportunity.

**Checklist:**
- [ ] Add `mcp` optional dependency (e.g., `mcp` SDK)
- [ ] Create `src/dbt_forge/mcp/server.py` — MCP server exposing tools:
  - `forge_doctor` — run health checks, return results
  - `forge_lint` — run lint rules, return violations
  - `forge_impact` — analyze downstream impact of a model
  - `forge_status` — return project stats
  - `forge_add_model` — scaffold a model (name, layer, columns)
  - `forge_init` — scaffold a project with given config
- [ ] Create `src/dbt_forge/mcp/__init__.py`
- [ ] Add entry point for `dbt-forge-mcp` server binary
- [ ] Add tests (mock MCP protocol)
- [ ] Add documentation page

### 5.1.2 `add mcp` Subcommand

Scaffold MCP server configuration for a dbt project — install dbt-mcp, configure tools, set up IDE config.

**Checklist:**
- [ ] Create `.cursor/mcp.json.j2` and `.vscode/mcp.json.j2` templates
- [ ] Add `add mcp` subcommand in `cli/add.py`
- [ ] Detect IDE (Cursor vs VS Code) and generate appropriate config
- [ ] Add tests

### 5.1.3 Contract Versioning

`dbt-forge contracts version <model>` — auto-create a new dbt model version when breaking changes are detected. Ties into `changelog` for detection.

**Checklist:**
- [ ] Implement model version YAML generation in `contracts.py`
- [ ] Detect breaking changes using `changelog.py` diffing
- [ ] Add `contracts version` subcommand in `cli/contracts_cmd.py`
- [ ] Generate versioned model file (`model_name_v2.sql` or inline version config)
- [ ] Add tests

### 5.1.4 Contract Diffing

`dbt-forge contracts diff` — show what changed between two versions of a model's contract (columns added/removed/type-changed).

**Checklist:**
- [ ] Implement contract diff logic in `contracts.py` (compare two YAML versions)
- [ ] Add `contracts diff` subcommand with `--from` / `--to` flags
- [ ] Rich table output showing added/removed/changed columns
- [ ] Add tests

### 5.1.5 Contract-First Init Mode

`dbt-forge init --contracts` — generate all mart models with `contract: { enforced: true }` from day one.

**Checklist:**
- [ ] Add `--contracts` flag to `init` command
- [ ] Update mart model templates to include contract config when flag is set
- [ ] Add contract-related packages (dbt-constraints) to generated `packages.yml`
- [ ] Add tests

---

## Phase 5.2: AI-Powered Code Generation

### 5.2.1 `dbt-forge explain <model>`

AI-powered model explanation — reads SQL, outputs business-friendly description of what the model does, its dependencies, and business logic.

**Checklist:**
- [ ] Add `explain` command in `cli/`
- [ ] Create explanation prompt in `llm/prompts.py`
- [ ] Read model SQL + upstream dependencies for context
- [ ] Rich markdown output in terminal
- [ ] Add tests

### 5.2.2 `dbt-forge review <model>`

AI code review for dbt best practices — checks naming, materialization choice, test coverage, SQL style, and suggests improvements.

**Checklist:**
- [ ] Add `review` command in `cli/`
- [ ] Create review prompt in `llm/prompts.py` (best practices checklist)
- [ ] Combine with `doctor` + `lint` findings for richer context
- [ ] Output actionable suggestions with severity levels
- [ ] Add tests

### 5.2.3 Natural Language Model Generation

`dbt-forge generate "Create a staging model for Stripe payments with deduplication"` — LLM generates SQL + YAML + tests from a natural language description.

**Checklist:**
- [ ] Add `generate` command in `cli/`
- [ ] Create generation prompt in `llm/prompts.py` (SQL + YAML + test generation)
- [ ] Parse LLM output into separate files (SQL, YAML, test YAML)
- [ ] Interactive review before writing
- [ ] Add tests

### 5.2.4 Smart `doctor --fix` with LLM

For lint violations that can't be auto-fixed with templates (e.g., fan-out queries, complex SQL), use LLM to suggest rewrites.

**Checklist:**
- [ ] Add `--ai-fix` flag to `doctor` and `lint` commands
- [ ] Create fix prompts in `llm/prompts.py` for each fixable rule
- [ ] Show proposed fix with diff, require confirmation
- [ ] Add tests

---

## Phase 5.3: Interactive TUI Workbench

A terminal UI providing a visual, interactive way to manage dbt projects without remembering CLI flags.

**Checklist:**
- [ ] Add `textual` dependency
- [ ] Create TUI app shell
- [ ] Implement project tree browser (models/sources/tests)
- [ ] Implement doctor check panel with interactive re-run
- [ ] Implement model/source/test add forms
- [ ] Implement DAG tree view (model dependencies)
- [ ] Add `tui` command in `main.py`
- [ ] Add tests

---

## Phase 6: Ecosystem & Extensibility

### 6.1 Plugin Architecture

Allow community extensions: custom generators, doctor checks, lint rules, and templates via Python entry points.

**Checklist:**
- [ ] Design plugin API and stable interfaces
- [ ] Implement entry point discovery (`dbt_forge.plugins` namespace)
- [ ] Plugin types: generators (new `add` commands), checks (new `doctor` rules), lint rules, template overrides
- [ ] Implement plugin loading and registration
- [ ] Add `dbt-forge plugins list` command
- [ ] Write plugin development guide
- [ ] Add tests

### 6.2 Custom Template Packs & Preset Registry

Share and discover templates and presets across teams and the community.

**Checklist:**
- [ ] Design template pack format (directory of `.j2` files + `metadata.yml`)
- [ ] `dbt-forge templates list` — browse available packs
- [ ] `dbt-forge templates install <name>` — install from GitHub/PyPI
- [ ] `dbt-forge preset list` / `dbt-forge preset install <name>` — curated preset registry
- [ ] Support preset inheritance: `extends: ["company-standard", "team-overrides"]`
- [ ] Set up registry repository
- [ ] Add tests

### 6.3 Observability Integrations

Bridge scaffolding and runtime monitoring — scaffold observability tool configs and track baselines.

**Checklist:**
- [ ] `dbt-forge add observability` — scaffold Elementary, Monte Carlo, or Soda integration (YAML configs, packages, alerting rules)
- [ ] CI report generation: `dbt-forge doctor --ci --report html` for CI artifacts
- [ ] Baseline tracking: store cost/performance baselines in `.dbt-forge.yml`, alert on regressions
- [ ] Create `src/dbt_forge/templates/observability/` with tool-specific configs
- [ ] Add tests

### 6.4 Mesh Maturity

Advanced dbt Mesh features for large-scale multi-project setups.

**Checklist:**
- [ ] `dbt-forge mesh graph` — cross-project dependency visualization (terminal DAG)
- [ ] Mesh doctor checks: circular cross-project deps, missing contracts on public models, unused cross-project refs
- [ ] `dbt-forge mesh migrate` — analyze monolith project and suggest Mesh split points (domain clustering)
- [ ] Multi-repo support: `dbt-forge mesh init --multi-repo` for separate git repos per sub-project
- [ ] Add tests

### 6.5 VS Code Extension

GUI layer on top of dbt-forge for VS Code / Cursor users.

**Checklist:**
- [ ] Set up VS Code extension project (TypeScript)
- [ ] Right-click context menus: "Add model here", "Add source", "Run doctor"
- [ ] Command palette integration for all forge commands
- [ ] Inline diagnostics from doctor/lint checks
- [ ] Status dashboard webview panel
- [ ] Publish to VS Code marketplace

---

## Priority Matrix

| Feature | Impact | Effort | Differentiation | Phase |
|---------|--------|--------|-----------------|-------|
| DX Quick Wins | Medium | Low | Medium | 5.0 |
| MCP Server | High | Medium | **Very High** | 5.1 |
| Contract Governance | High | Low-Med | High | 5.1 |
| AI Code Generation | High | Medium | High | 5.2 |
| TUI Workbench | Medium | Medium | Medium | 5.3 |
| Plugin Architecture | Medium | High | High | 6.1 |
| Template/Preset Registry | Medium | Medium | Medium | 6.2 |
| Observability | Medium | Medium | Medium | 6.3 |
| Mesh Maturity | Lower | Medium | Medium | 6.4 |
| VS Code Extension | Medium | High | Medium | 6.5 |
