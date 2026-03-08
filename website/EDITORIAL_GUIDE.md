# dbt-forge Editorial Guide

Use this guide for homepage copy, docs pages, and public descriptions in the website.
It is the source of truth for tone, terminology, and review criteria.

## Voice

- Prefer concrete outcomes over abstract benefits.
- State scope and limits plainly.
- Use short sentences with technical nouns instead of hype adjectives.
- Write for analytics engineers and dbt users, not for a generic SaaS audience.

## Canonical terminology

- Use `scaffold` for CLI actions that write project files.
- Use `dbt project` for the thing the CLI creates or extends.
- Use `starting structure` for the initial layout created by `init`.
- Use `starter models` for example SQL and YAML included in the scaffold.
- Use `template` only for implementation details such as adapter-specific files or CI files.
- Use `project structure` as the label for docs that explain the generated directories and files.
- Avoid switching between `repo`, `baseline`, `starter repo`, and `generated repo` when you mean `dbt project`.

## Anti-AI guardrails

- Do not use filler terms such as `seamless`, `powerful`, `robust`, or `streamline` unless the next sentence proves the claim.
- Do not stack vague adjectives such as `clean`, `scalable`, and `maintainable` without showing a concrete behavior or file.
- Replace generic value statements with one observable fact: a command, generated path, file, or constraint.
- Do not write sentences that could be pasted into an unrelated developer tool homepage without changes.

## Page template

Use this order unless a page has a strong reason not to:

1. Lead sentence with the concrete function of the page or feature.
2. Brief body that states scope and value.
3. Commands, examples, or generated output.
4. Constraints, defaults, or limits.

## Review checklist

- The first paragraph says what the tool or page is about in plain language.
- A skeptical engineer can identify the product boundary within 30 seconds.
- Claims map to real commands, files, or generated output.
- Headings are task-oriented in docs and specific on marketing pages.
- The page uses the canonical terminology list without synonym drift.
