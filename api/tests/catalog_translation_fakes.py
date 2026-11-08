"""Scripted IngredientTranslator for application tests (spec 073, T011). No network."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.ingredient_translation import (
    IngredientTranslationRequest,
    IngredientTranslationResult,
    TranslationUnavailable,
    TranslationUnparseable,
)


@dataclass
class FakeIngredientTranslator:
    """Answers from a script keyed by the requested name; records every call.

    `results` maps a name to an IngredientTranslationResult. `failures` maps a name to an
    exception class to raise. A name in neither gets an invalid answer, so a test cannot pass
    by accident.
    """

    results: dict[str, IngredientTranslationResult] = field(default_factory=dict)
    failures: dict[str, type[Exception]] = field(default_factory=dict)
    calls: list[IngredientTranslationRequest] = field(default_factory=list)

    def translate(self, request: IngredientTranslationRequest) -> IngredientTranslationResult:
        self.calls.append(request)
        if request.name in self.failures:
            raise self.failures[request.name]()
        return self.results.get(request.name, IngredientTranslationResult(False, None))


__all__ = [
    "FakeIngredientTranslator",
    "TranslationUnavailable",
    "TranslationUnparseable",
]
