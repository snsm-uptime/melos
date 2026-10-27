"""Ingredient catalog matching (spec 018, research §3 and §4): name normalization and the rule.

Pure: no I/O and no SDK imports (constitution §3). The model proposes a catalog entry for each
line; `match_line` confirms the proposal only when the line's name is the same name under the
normalization below, and rejects it otherwise.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

_SPACES = re.compile(r"\s+")
_VOWELS = frozenset("aeiou")

# English plurals whose singular ends in "f" or "fe" do not follow the "-s" rule.
_VES_TO_SINGULAR = {
    "leaves": "leaf",
    "loaves": "loaf",
    "halves": "half",
    "calves": "calf",
    "shelves": "shelf",
    "wolves": "wolf",
    "knives": "knife",
}


@dataclass(frozen=True)
class LineMatch:
    """The label on a draft line (FR-001). `entry` is set exactly when `kind` is "matched"."""

    kind: Literal["matched", "new"]
    entry: str | None = None


@dataclass(frozen=True)
class NameChange:
    """A listed change from the text's name to the catalog entry it matches (FR-003)."""

    line: int
    from_name: str
    to: str


NEW = LineMatch(kind="new")


def normalize_name(text: str) -> str:
    """Trim, drop accents, casefold and collapse spaces. Two names are the same when these match."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SPACES.sub(" ", without_accents.casefold()).strip()


def same_spelling(first: str, second: str) -> bool:
    """True when two names differ only in letter case or spaces, so no change is listed (FR-003)."""
    return _SPACES.sub(" ", first.casefold()).strip() == _SPACES.sub(" ", second.casefold()).strip()


def singular_forms(normalized: str) -> frozenset[str]:
    """The name and every singular it may be, from fixed English and Spanish rules."""
    forms = {normalized}
    word = normalized
    head, _, last = word.rpartition(" ")
    if last in _VES_TO_SINGULAR:
        forms.add(f"{head} {_VES_TO_SINGULAR[last]}".strip())
    if len(word) > 4 and word.endswith("ies"):
        forms.add(word[:-3] + "y")
    if len(word) > 4 and word.endswith("oes"):
        forms.add(word[:-2])
    if len(word) > 4 and word.endswith("es") and word[-3] not in _VOWELS:
        forms.add(word[:-2])
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        forms.add(word[:-1])
    return frozenset(forms)


def match_line(
    text_name: str | None,
    name: str,
    proposal: str | None,
    catalog: Sequence[str],
) -> LineMatch:
    """Confirm the model's proposal for one line, or reject it (research §3).

    A line matches only when the proposal is an entry of the catalog and the line's name is the
    same name as that entry, singular forms included. A line with no proposal is new.
    """
    if proposal is None or proposal not in catalog:
        return NEW
    line_key = normalize_name(text_name or name)
    entry_key = normalize_name(proposal)
    if entry_key in singular_forms(line_key) or line_key in singular_forms(entry_key):
        return LineMatch(kind="matched", entry=proposal)
    return NEW
