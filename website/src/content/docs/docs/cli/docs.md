---
title: docs generate
description: Command reference for AI-assisted model and column documentation generation.
---

`dbt-forge docs generate` scans a dbt project for models with missing descriptions and
uses an LLM to generate them. It reads the model SQL, sends it to a provider, and
presents the results for interactive review before writing to YAML.

## Command

```bash
dbt-forge docs generate [--model NAME] [--provider KEY] [--yes] [--delay SECONDS]
```

## What it does

1. **Scans** all model YAML files (`models/**/*.yml`) for models with empty `description` fields or columns with empty descriptions
2. **Reads** the corresponding `.sql` file for each undocumented model
3. **Sends** the model name, SQL, column names, and any existing descriptions to the selected LLM
4. **Displays** the generated descriptions in a table for review
5. **Writes** accepted descriptions back to the YAML file, preserving existing descriptions

## Options

### `--model`, `-m`

Generate docs for a specific model only. When omitted, all models with missing
descriptions are processed.

```bash
dbt-forge docs generate --model stg_orders
```

### `--provider`

Select the LLM provider. When omitted, the CLI auto-detects available providers from
environment variables and running services.

```bash
dbt-forge docs generate --provider claude
dbt-forge docs generate --provider openai
dbt-forge docs generate --provider ollama
```

### `--yes`, `-y`

Auto-accept all generated descriptions without interactive review.

### `--delay`

Seconds to wait between API calls. Defaults to `1.0`. Set to `0` for no delay.

## Providers

### Claude (Anthropic)

Requires the `anthropic` package and `ANTHROPIC_API_KEY` environment variable.

```bash
pip install dbt-forge[claude]
export ANTHROPIC_API_KEY=sk-ant-...
dbt-forge docs generate --provider claude
```

### OpenAI

Requires the `openai` package and `OPENAI_API_KEY` environment variable.

```bash
pip install dbt-forge[openai]
export OPENAI_API_KEY=sk-...
dbt-forge docs generate --provider openai
```

### Ollama (local)

No extra dependencies. Connects to Ollama at `localhost:11434` using stdlib HTTP.

```bash
ollama run llama3.2   # start Ollama first
dbt-forge docs generate --provider ollama
```

### Auto-detection

Without `--provider`, the CLI checks:

1. `ANTHROPIC_API_KEY` environment variable → Claude
2. `OPENAI_API_KEY` environment variable → OpenAI
3. Ollama running on `localhost:11434` → Ollama

If multiple providers are available, the CLI prompts for selection. If none are
available, the command exits with instructions.

## Interactive flow

For each undocumented model, the command:

1. Shows the model name and generated descriptions
2. Displays a table of column descriptions
3. Prompts to **Accept** or **Skip**

Accepted descriptions are written to the existing YAML file. Existing descriptions
(non-empty) are never overwritten.

## YAML preservation

The command updates descriptions in place:

- Empty model `description` fields are filled with the generated text
- Empty column `description` fields are filled with generated text
- Columns that already have descriptions are left unchanged
- The file structure (keys, ordering, other fields) is preserved

## Example

Before:

```yaml
models:
  - name: stg_orders
    description: ""
    columns:
      - name: order_id
        description: ""
      - name: amount
        description: "Total order amount in cents"
```

After running `dbt-forge docs generate --model stg_orders`:

```yaml
models:
  - name: stg_orders
    description: "Staging model that cleans and standardizes raw order data"
    columns:
      - name: order_id
        description: "Unique identifier for each order"
      - name: amount
        description: "Total order amount in cents"  # preserved
```

## Behavior and limits

- Requires a terminal for interactive review (unless `--yes` is used).
- The LLM generates descriptions based on SQL logic and column names. Review the output for accuracy.
- Rate limiting (`--delay`) is applied between models, not between column descriptions within a model.
- The command reads YAML with `pyyaml` and writes it back. Comments in YAML files are not preserved.
- Models without a corresponding `.sql` file are still processed — the LLM receives an empty SQL context.
