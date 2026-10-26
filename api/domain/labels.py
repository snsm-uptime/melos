"""Chip labels in the member's language (spec 016 FR-011, research R4). Pure: no I/O.

A label is shown in the member's account language. When it is missing there, the
other language is used. There is no text detection.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "es")


def pick_label(labels: dict[str, str], language: str) -> str:
    """The label in `language`, or in the other supported language when that one is missing."""
    if language in labels and labels[language]:
        return labels[language]
    for fallback in SUPPORTED_LANGUAGES:
        if labels.get(fallback):
            return labels[fallback]
    raise ValueError("a label needs at least one non-empty language")
