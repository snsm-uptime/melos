"""Pure kitchen create / rename rules (no FastAPI / SQLAlchemy)."""

from __future__ import annotations

from domain.errors import InvalidKitchenNameError

KITCHEN_NAME_MAX_LENGTH = 200


def validate_kitchen_name(raw: str) -> str:
    """Trim and validate a user-visible kitchen name.

    Returns the normalized name. Raises InvalidKitchenNameError when empty
    or whitespace-only after trim, or when longer than KITCHEN_NAME_MAX_LENGTH.
    """
    if raw is None:
        raise InvalidKitchenNameError()
    name = raw.strip()
    if not name:
        raise InvalidKitchenNameError()
    if len(name) > KITCHEN_NAME_MAX_LENGTH:
        raise InvalidKitchenNameError(
            f"Kitchen name must be at most {KITCHEN_NAME_MAX_LENGTH} characters."
        )
    return name
