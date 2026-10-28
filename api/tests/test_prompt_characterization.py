"""Characterization: the rendered prompts match the golden files (spec 018 T002).

The golden files hold the output of the prompt code before the templates moved into
adapters/llm/prompts/. A change here means the prompt text changed on purpose: regenerate the
golden file in the same commit.
"""

from __future__ import annotations

from pathlib import Path

from adapters.llm.prompt import build_contents, system_instruction

GOLDEN = Path(__file__).parent / "fixtures" / "prompts"

CATALOG_NAMES = ["onion", "flour", "salt"]
PASTED_TEXT = "Quick soup\n2 large onions\nFry the onions."


def test_system_instruction_matches_golden() -> None:
    expected = (GOLDEN / "recipe_extraction_system.golden.txt").read_text(encoding="utf-8")

    assert system_instruction() == expected


def test_build_contents_matches_golden() -> None:
    expected = (GOLDEN / "recipe_extraction_user.golden.txt").read_text(encoding="utf-8")

    assert build_contents(PASTED_TEXT, CATALOG_NAMES) == expected
