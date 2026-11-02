"""Notebook invite rules (spec 057 FR-002, FR-003)."""

from __future__ import annotations

import pytest
from domain.errors import NotebookNotShareableError, NotebookOwnerOnlyError
from domain.notebook_invite import (
    NOTEBOOK_INVITE_PATH,
    assert_can_manage_sharing,
    assert_shareable,
    build_notebook_invite_link,
)


def test_link_has_one_path_and_no_trailing_slash_issue() -> None:
    assert build_notebook_invite_link("https://melos.test/", "abc") == (
        f"https://melos.test{NOTEBOOK_INVITE_PATH}?token=abc"
    )


def test_personal_notebook_is_shareable() -> None:
    assert_shareable("personal")


def test_kitchen_notebook_is_not_shareable() -> None:
    with pytest.raises(NotebookNotShareableError):
        assert_shareable("kitchen")


def test_owner_manages_a_personal_notebook() -> None:
    assert_can_manage_sharing("personal", "owner")


def test_member_may_not_manage() -> None:
    with pytest.raises(NotebookOwnerOnlyError):
        assert_can_manage_sharing("personal", "member")


def test_kitchen_refusal_comes_before_the_owner_refusal() -> None:
    with pytest.raises(NotebookNotShareableError):
        assert_can_manage_sharing("kitchen", "kitchen_member")
