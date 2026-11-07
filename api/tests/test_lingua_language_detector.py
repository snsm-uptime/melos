"""The offline language detector on lingua (spec 043 FR-005a). No network, no model call."""

from __future__ import annotations

from pathlib import Path

import pytest
from adapters.language.lingua_detector import LinguaLanguageDetector

LANGUAGE_CASES = Path(__file__).parent / "fixtures" / "ai_eval" / "language"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Sopa de lentejas\n\nlenteja\ncebolla\n\nLavar las lentejas.\nCocinar 30 minutos.", "es"),
        ("Lentil soup\n\nlentil\nonion\n\nRinse the lentils.\nSimmer for 30 minutes.", "en"),
        ("   ", None),
        ("", None),
    ],
)
def test_it_tells_english_from_spanish(text: str, expected: str | None) -> None:
    assert LinguaLanguageDetector().detect(text) == expected


def test_the_evaluation_set_matches() -> None:
    """The ten cases of fixtures/ai_eval/language/CASES.md, answered offline."""
    expected: dict[str, str] = {}
    for row in (LANGUAGE_CASES / "CASES.md").read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0].endswith(".txt"):
            expected[cells[0]] = cells[1]
    assert len(expected) == 10
    detector = LinguaLanguageDetector()
    found = {
        name: detector.detect((LANGUAGE_CASES / name).read_text(encoding="utf-8"))
        for name in expected
    }
    assert found == expected
