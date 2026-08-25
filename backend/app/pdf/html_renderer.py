"""Render resume HTML from structured content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.pdf.template_context import build_template_context

_TEMPLATE_DIR = Path(__file__).resolve().parent
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_resume_html(content: dict[str, Any]) -> str:
    """Render ATS-friendly HTML for a resume version's stored content."""
    context = build_template_context(content)
    template = _ENV.get_template("resume_template.html")
    return template.render(**context)
