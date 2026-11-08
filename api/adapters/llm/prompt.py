"""Prompt for the Gemini recipe extractor.

The prompt text lives in adapters/llm/prompts/ as single-purpose templates (see its README).
This module fills them. The pasted text is delimited as data (FR-007, constitution §4).
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from adapters.llm.prompt_templates import load_template, render

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


def system_instruction() -> str:
    return render(
        "recipe_extraction_system",
        TEXT_OPEN=TEXT_OPEN,
        TEXT_CLOSE=TEXT_CLOSE,
        NAMES_OPEN=NAMES_OPEN,
        NAMES_CLOSE=NAMES_CLOSE,
        # MVP-OUT: MAIN_KEYS=", ".join(vocabulary.main_ingredient_keys),
        VAGUE_PHRASES=VAGUE_PHRASES,
    )


def page_part_system_instruction() -> str:
    """System instruction for one part of a web page (spec 026, partial page mode)."""
    return render(
        "recipe_extraction_page_part_system",
        TEXT_OPEN=TEXT_OPEN,
        TEXT_CLOSE=TEXT_CLOSE,
        NAMES_OPEN=NAMES_OPEN,
        NAMES_CLOSE=NAMES_CLOSE,
        VAGUE_PHRASES=VAGUE_PHRASES,
    )


def build_contents(
    text: str, ingredient_names: Sequence[str], part: tuple[int, int] | None = None
) -> str:
    """User turn: the pasted text and the catalog names, each in its own delimited block.

    With `part` (index from 1, total), one line before the blocks says which part of the page
    this is. Without it the turn is exactly the text-capture one.
    """
    turn = _user_turn(text, ingredient_names)
    if part is None:
        return turn
    index, total = part
    line = render("recipe_extraction_page_part_line", PART=str(index), TOTAL=str(total))
    return f"{line}\n\n{turn}"


def _user_turn(text: str, ingredient_names: Sequence[str]) -> str:
    return render(
        "recipe_extraction_user",
        TEXT_OPEN=TEXT_OPEN,
        TEXT=text.replace(TEXT_CLOSE, ""),
        TEXT_CLOSE=TEXT_CLOSE,
        NAMES_OPEN=NAMES_OPEN,
        NAMES_JSON=json.dumps(sorted(set(ingredient_names)), ensure_ascii=False),
        NAMES_CLOSE=NAMES_CLOSE,
    )


def _shared_ingredient_line_rules() -> str:
    """The ingredient-line block of the page-part template, verbatim, so both prompts agree.

    Cut from the template text between `- ingredient_lines:` and `- steps:`; the vague phrases
    are filled here the same way the page-part prompt fills them.
    """
    template = load_template("recipe_extraction_page_part_system")
    start = template.index("- ingredient_lines:")
    end = template.index("- steps:")
    return template[start:end].replace("{{VAGUE_PHRASES}}", VAGUE_PHRASES)


def picture_system_instruction() -> str:
    """System instruction for one cookbook photo (spec 041, FR-019 to FR-022)."""
    return render(
        "recipe_extraction_picture_system",
        NAMES_OPEN=NAMES_OPEN,
        NAMES_CLOSE=NAMES_CLOSE,
        INGREDIENT_LINE_RULES=_shared_ingredient_line_rules(),
    )


def build_picture_contents(ingredient_names: Sequence[str]) -> str:
    """User turn for a photo: the catalog names block and one line. The image is sent beside it.

    The closing marker is cut out of each name, so no catalog name can close the block.
    """
    names = [name.replace(NAMES_CLOSE, "") for name in ingredient_names]
    return render(
        "recipe_extraction_picture_user",
        NAMES_OPEN=NAMES_OPEN,
        NAMES_JSON=json.dumps(sorted(set(names)), ensure_ascii=False),
        NAMES_CLOSE=NAMES_CLOSE,
    )
