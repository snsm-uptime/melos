"""Prompt for the Gemini recipe extractor.

The prompt text lives in adapters/llm/prompts/ as single-purpose templates (see its README).
This module fills them. The pasted text is delimited as data (FR-007, constitution §4).
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from domain.recipe_draft import Vocabulary

from adapters.llm.prompt_templates import render

TEXT_OPEN = "<<<RECIPE_TEXT"
TEXT_CLOSE = "RECIPE_TEXT>>>"
NAMES_OPEN = "<<<CATALOG_NAMES"
NAMES_CLOSE = "CATALOG_NAMES>>>"

VAGUE_PHRASES = (
    '"to taste", "a pinch (of)", "a dash (of)", "a splash (of)", '
    '"a drizzle (of)", "some", "a little". '
    'Spanish: "al gusto", "un poco (de)", "mucho", "la mitad (de)", '
    '"una pizca (de)", "algo de", "unas gotas (de)", "un chorrito (de)"'
)


def system_instruction(vocabulary: Vocabulary) -> str:
    return render(
        "recipe_extraction_system",
        TEXT_OPEN=TEXT_OPEN,
        TEXT_CLOSE=TEXT_CLOSE,
        NAMES_OPEN=NAMES_OPEN,
        NAMES_CLOSE=NAMES_CLOSE,
        MAIN_KEYS=", ".join(vocabulary.main_ingredient_keys),
        VAGUE_PHRASES=VAGUE_PHRASES,
    )


def build_contents(text: str, ingredient_names: Sequence[str]) -> str:
    """User turn: the pasted text and the catalog names, each in its own delimited block."""
    return render(
        "recipe_extraction_user",
        TEXT_OPEN=TEXT_OPEN,
        TEXT=text.replace(TEXT_CLOSE, ""),
        TEXT_CLOSE=TEXT_CLOSE,
        NAMES_OPEN=NAMES_OPEN,
        NAMES_JSON=json.dumps(sorted(set(ingredient_names)), ensure_ascii=False),
        NAMES_CLOSE=NAMES_CLOSE,
    )
