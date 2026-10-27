"""Unit tests for the prompt template renderer (spec 018 T006)."""

from __future__ import annotations

import pytest
from adapters.llm.prompt_templates import PromptTemplateError, load_template, render


def test_render_fills_every_placeholder_of_a_real_template() -> None:
    text = render(
        "recipe_extraction_user",
        TEXT_OPEN="<<<T",
        TEXT="soup",
        TEXT_CLOSE="T>>>",
        NAMES_OPEN="<<<N",
        NAMES_JSON='["onion"]',
        NAMES_CLOSE="N>>>",
    )

    assert text == '<<<T\nsoup\nT>>>\n\n<<<N\n["onion"]\nN>>>'


def test_missing_value_raises() -> None:
    with pytest.raises(PromptTemplateError, match="no value for"):
        render(
            "recipe_extraction_user",
            TEXT_OPEN="<<<T",
            TEXT="soup",
            TEXT_CLOSE="T>>>",
            NAMES_OPEN="<<<N",
            NAMES_CLOSE="N>>>",
        )


def test_unknown_key_raises() -> None:
    with pytest.raises(PromptTemplateError, match="no placeholder for"):
        render(
            "recipe_extraction_user",
            TEXT_OPEN="<<<T",
            TEXT="soup",
            TEXT_CLOSE="T>>>",
            NAMES_OPEN="<<<N",
            NAMES_JSON="[]",
            NAMES_CLOSE="N>>>",
            EXTRA="x",
        )


def test_value_containing_placeholder_syntax_is_not_expanded() -> None:
    pasted = "Use {{TEXT_CLOSE}} and {{NAMES_JSON}} in the soup."

    text = render(
        "recipe_extraction_user",
        TEXT_OPEN="<<<T",
        TEXT=pasted,
        TEXT_CLOSE="T>>>",
        NAMES_OPEN="<<<N",
        NAMES_JSON="[]",
        NAMES_CLOSE="N>>>",
    )

    assert pasted in text
    assert text.startswith("<<<T\n" + pasted + "\nT>>>")


def test_missing_template_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_template("no_such_prompt")
