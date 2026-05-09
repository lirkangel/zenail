from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape([]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


class TemplateRenderError(Exception):
    pass


def render(template_key: str, lang: str, payload: dict[str, Any]) -> tuple[str | None, str]:
    """Return (subject, body). Email templates put the subject on line 1 and an empty line before the body."""
    template_path = f"{lang}/{template_key}.txt"
    try:
        template = _env.get_template(template_path)
    except Exception as exc:  # jinja2.TemplateNotFound, etc.
        raise TemplateRenderError(f"Missing template: {template_path}") from exc
    rendered = template.render(**payload).strip("\n")
    if "\n\n" in rendered and template_key.endswith(".email"):
        subject, body = rendered.split("\n\n", 1)
        return subject.strip(), body.strip()
    return None, rendered
