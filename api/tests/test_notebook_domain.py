"""Pure notebook rules (spec 055 FR-003, FR-005)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from domain.errors import InvalidNotebookOwnerError, NotebookNotFoundError
from domain.notebook import Notebook, default_notebook_name


def test_kitchen_notebook_kind() -> None:
    notebook = Notebook(id=uuid4(), kitchen_id=uuid4())
    assert notebook.kind == "kitchen"
    assert notebook.name is None


def test_member_notebook_kind() -> None:
    notebook = Notebook(id=uuid4(), user_id=uuid4(), name="ana's Notebook")
    assert notebook.kind == "member"


def test_notebook_with_both_owners_rejected() -> None:
    with pytest.raises(InvalidNotebookOwnerError):
        Notebook(id=uuid4(), kitchen_id=uuid4(), user_id=uuid4())


def test_notebook_without_owner_rejected() -> None:
    with pytest.raises(InvalidNotebookOwnerError):
        Notebook(id=uuid4())


def test_default_notebook_name_uses_alias() -> None:
    assert default_notebook_name("ana") == "ana's Notebook"


def test_notebook_not_found_has_one_fixed_message() -> None:
    assert str(NotebookNotFoundError()) == NotebookNotFoundError.MESSAGE
    assert NotebookNotFoundError.CODE == "notebook_not_found"
