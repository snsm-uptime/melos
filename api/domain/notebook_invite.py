"""Notebook invite rules (spec 057; no I/O).

The token, expiry and email rules are the kitchen invite's, in domain/kitchen_invite.py. Only
what differs lives here: one link for everyone, and who may manage a notebook's sharing.
"""

from __future__ import annotations

from domain.errors import NotebookNotShareableError, NotebookOwnerOnlyError
from domain.notebook import NotebookAccess, NotebookKind

NOTEBOOK_INVITE_PATH = "/invites/notebook"

# The 410 body of every dead link. InvalidInviteTokenError's own text speaks of a kitchen.
INVALID_NOTEBOOK_INVITE_MESSAGE = (
    "This invite link is invalid or has expired. Ask the notebook owner for a new invite."
)


def build_notebook_invite_link(public_app_url: str, raw_token: str) -> str:
    return f"{public_app_url.rstrip('/')}{NOTEBOOK_INVITE_PATH}?token={raw_token}"


def assert_shareable(kind: NotebookKind) -> None:
    """A kitchen notebook's people come from the kitchen (FR-003)."""
    if kind != "personal":
        raise NotebookNotShareableError()


def assert_can_manage_sharing(kind: NotebookKind, access: NotebookAccess) -> None:
    """Inviting and removing belong to the owner of a personal notebook (FR-002, FR-003)."""
    assert_shareable(kind)
    if access != "owner":
        raise NotebookOwnerOnlyError()
