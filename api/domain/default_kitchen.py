"""Which kitchen Home opens (spec 064, data-model.md). Pure rule, no I/O."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MemberKitchen:
    id: UUID
    is_archived: bool
    is_owner: bool
    created_at: datetime
    joined_at: datetime


def resolve_default_kitchen(stored: UUID | None, kitchens: Sequence[MemberKitchen]) -> UUID | None:
    """The stored kitchen if usable, else earliest owned, else earliest joined, else none."""
    active = [kitchen for kitchen in kitchens if not kitchen.is_archived]
    if any(kitchen.id == stored for kitchen in active):
        return stored
    owned = [kitchen for kitchen in active if kitchen.is_owner]
    if owned:
        return min(owned, key=lambda kitchen: (kitchen.created_at, kitchen.id)).id
    if active:
        return min(active, key=lambda kitchen: (kitchen.joined_at, kitchen.id)).id
    return None
