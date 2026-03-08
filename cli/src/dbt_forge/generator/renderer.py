"""Jinja2 template renderer."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(template_path: str, context: dict) -> str:
    """Render a template file relative to the templates directory."""
    env = get_env()
    template = env.get_template(template_path)
    return template.render(**context)


def render_string(source: str, context: dict) -> str:
    """Render an inline Jinja2 string."""
    env = get_env()
    return env.from_string(source).render(**context)
