"""Who may rename or delete a notebook (spec 059, data-model.md "Permission rule")."""

from __future__ import annotations

import pytest
from domain.errors import KitchenArchivedError, NotebookOwnerOnlyError
from domain.notebook import assert_can_manage


def test_the_owner_of_a_personal_notebook_may_manage_it() -> None:
    assert_can_manage("owner", None)


def test_a_member_of_a_personal_notebook_may_not() -> None:
    with pytest.raises(NotebookOwnerOnlyError):
        assert_can_manage("member", None)


def test_a_member_of_an_active_kitchen_may_manage_its_notebooks() -> None:
    assert_can_manage("kitchen_member", False)


def test_a_member_of_an_archived_kitchen_may_not() -> None:
    with pytest.raises(KitchenArchivedError):
        assert_can_manage("kitchen_member", True)
