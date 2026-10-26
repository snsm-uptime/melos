"""Chip label rules (spec 016 FR-011, research R4). Pure pytest, no I/O."""

from __future__ import annotations

import pytest
from domain.labels import pick_label

LABELS = {"en": "Poultry", "es": "Aves"}


@pytest.mark.parametrize(("language", "expected"), [("en", "Poultry"), ("es", "Aves")])
def test_label_is_shown_in_the_members_language(language: str, expected: str) -> None:
    assert pick_label(LABELS, language) == expected


def test_missing_label_falls_back_to_the_other_language() -> None:
    assert pick_label({"en": "Oaxacan"}, "es") == "Oaxacan"
    assert pick_label({"es": "Oaxaqueña"}, "en") == "Oaxaqueña"


def test_empty_label_counts_as_missing() -> None:
    assert pick_label({"en": "", "es": "Aves"}, "en") == "Aves"


def test_label_with_no_text_in_any_language_is_refused() -> None:
    with pytest.raises(ValueError):
        pick_label({"en": "", "es": ""}, "en")
