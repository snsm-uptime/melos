"""LanguageDetector on lingua-py: English or Spanish from text, offline (spec 043 FR-005a).

No model call and no network: lingua compares the text with its statistical models of the two
languages the app supports. Built once per process and shared; detection is thread-safe.
"""

from __future__ import annotations

import threading

from lingua import Language, LanguageDetector, LanguageDetectorBuilder

_CODES = {Language.ENGLISH: "en", Language.SPANISH: "es"}
# Below this gap between the two languages' confidence the answer is "unsure" (None), so a
# text in neither language, or too short to tell, gets no language.
MIN_RELATIVE_DISTANCE = 0.1

_lock = threading.Lock()
_shared: LanguageDetector | None = None


def _detector() -> LanguageDetector:
    global _shared
    with _lock:
        if _shared is None:
            _shared = (
                LanguageDetectorBuilder.from_languages(*_CODES)
                .with_minimum_relative_distance(MIN_RELATIVE_DISTANCE)
                .build()
            )
        return _shared


class LinguaLanguageDetector:
    """Production LanguageDetector: 'en', 'es', or None when unsure."""

    def detect(self, text: str) -> str | None:
        if not text.strip():
            return None
        found = _detector().detect_language_of(text)
        return None if found is None else _CODES.get(found)
