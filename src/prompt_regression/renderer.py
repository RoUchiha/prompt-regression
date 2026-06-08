"""Jinja2 template renderer for prompt templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, BaseLoader


def render_template(template_str: str, inputs: Dict[str, Any]) -> str:
    """Render a Jinja2 template string with the given inputs."""
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(template_str)
    return tmpl.render(**inputs)


def render_file(template_path: Path, inputs: Dict[str, Any]) -> str:
    """Render a Jinja2 template file."""
    env = Environment(loader=FileSystemLoader(str(template_path.parent)))
    tmpl = env.get_template(template_path.name)
    return tmpl.render(**inputs)
