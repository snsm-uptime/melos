"""Membership ACL policy — kitchen-scoped actions (Story 1.5.4 / 2.2).

Pure domain: no FastAPI / SQLAlchemy imports.
"""

from __future__ import annotations

from typing import Literal

# Stable action vocabulary. Kitchen content (recipes, carts, chat) adds its
# actions here as those features land; unknown actions fail closed.
KitchenAccessAction = Literal[
    "read_kitchen",
    "set_last_opened_kitchen",
    "rename_kitchen",
    "invite_member",
]

# Synonyms that normalize to an existing capability. Empty until a feature
# needs one.
_ACTION_ALIASES: dict[str, str] = {}

_MEMBER_READ_ACTIONS = frozenset(
    {
        "read_kitchen",
    }
)

_MEMBER_MUTATION_ACTIONS = frozenset(
    {
        "set_last_opened_kitchen",
    }
)

_OWNER_ACTIONS = frozenset(
    {
        "rename_kitchen",
        "invite_member",
    }
)

ALL_KNOWN_ACTIONS = (
    _MEMBER_READ_ACTIONS | _MEMBER_MUTATION_ACTIONS | _OWNER_ACTIONS | frozenset(_ACTION_ALIASES)
)


def normalize_kitchen_action(action: str) -> str | None:
    """Return canonical action name, or None if unknown (fail closed)."""
    if action in _ACTION_ALIASES:
        return _ACTION_ALIASES[action]
    if action in ALL_KNOWN_ACTIONS:
        return action
    return None


def is_member_read_action(canonical_action: str) -> bool:
    return canonical_action in _MEMBER_READ_ACTIONS


def is_member_mutation_action(canonical_action: str) -> bool:
    return canonical_action in _MEMBER_MUTATION_ACTIONS


def is_owner_action(canonical_action: str) -> bool:
    return canonical_action in _OWNER_ACTIONS


def deny_as_not_found_for_action(canonical_action: str) -> bool:
    """Kitchen-scoped reads hide existence (404). Mutations use 403 not_kitchen_member."""
    return is_member_read_action(canonical_action)
