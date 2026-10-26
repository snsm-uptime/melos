"""Notebook rules (no FastAPI / SQLAlchemy).

A personal notebook belongs to people: one owner and any number of members.
A kitchen notebook belongs to one kitchen: its members read and write it, and
it stores one owner (the member who created it). Recipes and the ingredient
catalog point at the notebook id, never at the owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from domain.errors import (
    InvalidNotebookError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
)

NotebookKind = Literal["personal", "kitchen"]
NotebookRole = Literal["owner", "member"]
NotebookAccess = Literal["owner", "member", "kitchen_member"]


@dataclass(frozen=True, slots=True)
class Notebook:
    id: UUID
    name: str
    kitchen_id: UUID | None = None
    # Origin label of a snapshot (S-035 sets it). Only a kitchen notebook may carry one.
    source_notebook_id: UUID | None = None
    # The member who created a kitchen notebook (FR-002). A personal notebook keeps
    # its owner in notebook_membership instead.
    owner_user_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidNotebookError()
        if self.source_notebook_id is not None and self.kitchen_id is None:
            raise InvalidNotebookError()
        if self.source_notebook_id == self.id:
            raise InvalidNotebookError()
        if self.owner_user_id is not None and self.kitchen_id is None:
            raise InvalidNotebookError()

    @property
    def kind(self) -> NotebookKind:
        return "kitchen" if self.kitchen_id is not None else "personal"


def default_notebook_name(alias: str) -> str:
    """Name of a person's default personal notebook, fixed at creation time."""
    return f"{alias}'s Notebook"


def kitchen_notebook_name(alias: str, kitchen_name: str) -> str:
    """Name of a kitchen notebook, fixed at creation time; it names the member who made it."""
    return f"{alias}'s ({kitchen_name}) Notebook"


def notebook_access(
    kind: NotebookKind, role: NotebookRole | None, in_kitchen: bool
) -> NotebookAccess | None:
    """What the caller may do with a notebook, or None when they may not see it (FR-014 to FR-017).

    A personal notebook gives the caller's role; kitchen membership never counts.
    A kitchen notebook gives kitchen_member to members of its kitchen; a role never counts.
    """
    if kind == "personal":
        return role
    return "kitchen_member" if in_kitchen else None


def choose_capture_notebook(candidates: list[UUID], picked: UUID | None) -> UUID | None:
    """The notebook a capture goes into, or None when the step must create one (FR-009, FR-011).

    With none or one candidate a pick is ignored. With several, the pick must be one of them.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if picked is None:
        raise NotebookChoiceRequiredError(list(candidates))
    if picked not in candidates:
        raise NotebookNotFoundError()
    return picked
