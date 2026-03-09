"""Prompt engineering for LLM description generation."""

from __future__ import annotations

import json
import re

from dbt_forge.llm.base import GeneratedDescription


def build_description_prompt(
    model_name: str,
    sql: str,
    columns: list[str],
    existing_descriptions: dict[str, str] | None = None,
) -> str:
    """Build a prompt for generating model and column descriptions."""
    parts = [
        "You are a dbt documentation expert. Generate clear, concise descriptions "
        "for a dbt model and its columns based on the SQL logic below.",
        "",
        f"Model name: {model_name}",
        "",
        "SQL:",
        "```sql",
        sql,
        "```",
        "",
        f"Columns: {', '.join(columns)}",
    ]

    if existing_descriptions:
        parts.extend(
            [
                "",
                "Existing descriptions (only fill in missing ones):",
                json.dumps(existing_descriptions, indent=2),
            ]
        )

    parts.extend(
        [
            "",
            "Respond with ONLY a JSON object in this exact format (no markdown, no backticks):",
            "{",
            '  "model_description": "One-sentence description of what this model does",',
            '  "columns": {',
            '    "column_name": "Description of what this column represents"',
            "  }",
            "}",
            "",
            "Include ALL columns listed above. Be specific and concise.",
        ]
    )

    return "\n".join(parts)


def parse_description_response(model_name: str, response_text: str) -> GeneratedDescription:
    """Parse LLM response into a GeneratedDescription."""
    # Try to extract JSON from the response
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        # Remove first and last lines
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    # Try to find JSON object in the response
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        text = json_match.group()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return GeneratedDescription(
            model_name=model_name,
            model_description="",
            column_descriptions={},
        )

    return GeneratedDescription(
        model_name=model_name,
        model_description=data.get("model_description", ""),
        column_descriptions=data.get("columns", {}),
    )
