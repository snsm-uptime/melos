"""A person's units: the list they can use, and what a save adds to it (spec 055)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import UUID

from domain.recipe_draft import (
    ALLOWED_UNITS,
    IngredientLine,
    InvalidDraftError,
    custom_unit_name,
    lookup_unit,
)

from application.ports import UnitRepository


def available_units(extras: Iterable[str]) -> tuple[str, ...]:
    """The ten in their usual order, then the person's others sorted (R20)."""
    return (*ALLOWED_UNITS, *sorted(set(extras) - set(ALLOWED_UNITS)))


def _offerable(words: Iterable[str]) -> tuple[str, ...]:
    names = (custom_unit_name(word) for word in words)
    return tuple(dict.fromkeys(name for name in names if name is not None))


def allowed_for_save(available: Sequence[str], keep_units: Iterable[str]) -> tuple[str, ...]:
    """What a saved line may use: the person's units and the words they said yes to (R10)."""
    return (*available, *_offerable(keep_units))


def _covered(word: str, available: Sequence[str]) -> bool:
    try:
        return lookup_unit(word, available) is not None
    except InvalidDraftError:
        return True


def kept_units_to_add(
    keep_units: Iterable[str],
    saved_lines: Iterable[IngredientLine],
    available: Sequence[str],
) -> tuple[str, ...]:
    """Kept words a saved line uses, leaving out what the person already has (R10)."""
    used = {line.unit for line in saved_lines}
    return tuple(
        word for word in _offerable(keep_units) if word in used and not _covered(word, available)
    )


@dataclass(frozen=True, slots=True)
class RemoveUserFromUnitsCommand:
    user_id: UUID


class RemoveUserFromUnitsService:
    """Take a deleted account off every unit (spec 055 FR-020b). S-054 must call this.

    It runs in the caller's transaction, the one that deletes the user row, and never commits.
    An array can't have a foreign key, so nothing else removes the id. There is no route.
    """

    def __init__(self, units: UnitRepository) -> None:
        self._units = units

    def execute(self, command: RemoveUserFromUnitsCommand) -> None:
        self._units.remove_user(command.user_id)
