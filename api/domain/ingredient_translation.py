"""Pure types and rules for AI-validated ingredient translation (spec 073).

No SDK or framework imports (constitution 3). The model answers with a validity flag and one
translation; this module decides whether that answer may be saved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "es"]

MAX_TRANSLATION_LENGTH = 80
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("en", "es")


class TranslationUnavailable(Exception):
    """The model could not be reached, or refused the call (timeout, network, quota)."""


class TranslationQuotaExceeded(TranslationUnavailable):
    """The model refused for quota or rate limit; the run stops early (translation-port.md)."""


class TranslationUnparseable(Exception):
    """The model answered, but not in the expected shape."""


class MissingLanguageError(ValueError):
    """A standard ingredient has no language, so its other-language name has no target."""


class InvalidTranslationResult(ValueError):
    """A result breaks the rules: a valid answer needs a clean translation, an invalid one none."""


@dataclass(frozen=True, slots=True)
class IngredientTranslationRequest:
    name: str
    source_language: Language
    target_language: Language


@dataclass(frozen=True, slots=True)
class IngredientTranslationResult:
    valid: bool
    translation: str | None

    def __post_init__(self) -> None:
        if self.valid:
            if not self.translation or self.translation != self.translation.strip():
                raise InvalidTranslationResult("a valid translation must be non-empty and trimmed")
            if len(self.translation) > MAX_TRANSLATION_LENGTH:
                raise InvalidTranslationResult("a translation is at most 80 characters")
            if "\n" in self.translation or "\r" in self.translation:
                raise InvalidTranslationResult("a translation has no newline")
        elif self.translation is not None:
            raise InvalidTranslationResult("an invalid answer has no translation")


def target_language(source: Language | None) -> Language:
    """The other supported language. A missing source has no target (spec 073, T027)."""
    if source == "en":
        return "es"
    if source == "es":
        return "en"
    raise MissingLanguageError("a standard ingredient needs a language to translate it")
