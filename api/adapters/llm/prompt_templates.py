"""Load prompt templates from adapters/llm/prompts/ and fill their placeholders.

A placeholder is `{{NAME}}`. Values are inserted in one pass, so a value that contains
`{{…}}` (pasted text, for example) stays as text and is never expanded again.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class PromptTemplateError(ValueError):
    """A template and its values do not match."""


@cache
def load_template(name: str) -> str:
    """The text of `prompts/<name>.md`. Raises FileNotFoundError when it does not exist."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def render(name: str, **values: str) -> str:
    """Fill every `{{key}}` in the template with its value, once each."""
    template = load_template(name)
    needed = set(_PLACEHOLDER.findall(template))
    given = set(values)
    if missing := needed - given:
        raise PromptTemplateError(f"{name}: no value for {', '.join(sorted(missing))}")
    if unknown := given - needed:
        raise PromptTemplateError(f"{name}: no placeholder for {', '.join(sorted(unknown))}")
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
