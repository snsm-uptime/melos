"""Notebook ownership rules (no FastAPI / SQLAlchemy).

A notebook is owned by exactly one kitchen or one member. Recipes and the
ingredient catalog point at the notebook id, never at the owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from domain.errors import InvalidNotebookOwnerError

NotebookKind = Literal["kitchen", "member"]


@dataclass(frozen=True, slots=True)
class Notebook:
    id: UUID
    kitchen_id: UUID | None = None
    user_id: UUID | None = None
    # Set for member notebooks only; a kitchen notebook shows the kitchen's name.
    name: str | None = None

    def __post_init__(self) -> None:
        if (self.kitchen_id is None) == (self.user_id is None):
            raise InvalidNotebookOwnerError()

    @property
    def kind(self) -> NotebookKind:
        return "kitchen" if self.kitchen_id is not None else "member"


def default_notebook_name(alias: str) -> str:
    """Name of a member's default notebook, fixed at creation time."""
    return f"{alias}'s Notebook"
