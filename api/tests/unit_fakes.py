"""A fake UnitRepository shared by the application tests (spec 055)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class FakeUnits:
    extras: dict[UUID, list[str]] = field(default_factory=dict)
    added: list[tuple[list[str], UUID]] = field(default_factory=list)
    default_extras: list[str] = field(default_factory=list)

    def extras_for(self, user_id: UUID) -> list[str]:
        return list(self.extras.get(user_id, self.default_extras))

    def add_user(self, names: Sequence[str], user_id: UUID) -> None:
        self.added.append((list(names), user_id))
