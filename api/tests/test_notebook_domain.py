"""Pure notebook rules (spec 056 FR-001 to FR-011, data-model.md "Domain")."""

from __future__ import annotations

from uuid import uuid4

import pytest
from domain.errors import (
    InvalidNotebookError,
    KitchenArchivedError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
)
from domain.notebook import (
    Notebook,
    choose_capture_notebook,
    default_notebook_name,
    kitchen_notebook_name,
    notebook_access,
)


def test_personal_notebook_kind() -> None:
    notebook = Notebook(id=uuid4(), name="ana's Notebook")
    assert notebook.kind == "personal"
    assert notebook.kitchen_id is None


def test_kitchen_notebook_kind() -> None:
    notebook = Notebook(id=uuid4(), name="ana's (Home) Notebook", kitchen_id=uuid4())
    assert notebook.kind == "kitchen"


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_rejected(name: str) -> None:
    with pytest.raises(InvalidNotebookError):
        Notebook(id=uuid4(), name=name)


def test_origin_on_personal_notebook_rejected() -> None:
    with pytest.raises(InvalidNotebookError):
        Notebook(id=uuid4(), name="ana's Notebook", source_notebook_id=uuid4())


def test_origin_equal_to_own_id_rejected() -> None:
    notebook_id = uuid4()
    with pytest.raises(InvalidNotebookError):
        Notebook(
            id=notebook_id,
            name="ana's (Home) Notebook",
            kitchen_id=uuid4(),
            source_notebook_id=notebook_id,
        )


def test_owner_on_personal_notebook_rejected() -> None:
    with pytest.raises(InvalidNotebookError):
        Notebook(id=uuid4(), name="ana's Notebook", owner_user_id=uuid4())


def test_default_notebook_name_uses_alias() -> None:
    assert default_notebook_name("ana") == "ana's Notebook"


def test_kitchen_notebook_name_uses_alias_and_kitchen() -> None:
    assert kitchen_notebook_name("ana", "Home") == "ana's (Home) Notebook"


def test_personal_access_is_the_callers_role() -> None:
    assert notebook_access("personal", "owner", in_kitchen=False) == "owner"
    assert notebook_access("personal", "member", in_kitchen=False) == "member"


def test_personal_access_ignores_kitchen_membership() -> None:
    assert notebook_access("personal", None, in_kitchen=True) is None


def test_kitchen_access_is_kitchen_member_only_for_members() -> None:
    assert notebook_access("kitchen", None, in_kitchen=True) == "kitchen_member"
    assert notebook_access("kitchen", "owner", in_kitchen=False) is None


def test_capture_with_no_candidates_creates_one() -> None:
    assert choose_capture_notebook([], None) is None


def test_capture_with_no_candidates_ignores_a_pick() -> None:
    assert choose_capture_notebook([], uuid4()) is None


def test_capture_with_one_candidate_uses_it_without_a_pick() -> None:
    only = uuid4()
    assert choose_capture_notebook([only], None) == only


def test_capture_with_one_candidate_ignores_a_stale_pick() -> None:
    only = uuid4()
    assert choose_capture_notebook([only], uuid4()) == only


def test_capture_with_several_uses_the_pick() -> None:
    first, second = uuid4(), uuid4()
    assert choose_capture_notebook([first, second], second) == second


def test_capture_with_several_and_a_stale_pick_is_refused() -> None:
    first, second = uuid4(), uuid4()
    with pytest.raises(NotebookNotFoundError):
        choose_capture_notebook([first, second], uuid4())


def test_capture_with_several_and_no_pick_asks_for_a_choice() -> None:
    first, second = uuid4(), uuid4()
    with pytest.raises(NotebookChoiceRequiredError) as raised:
        choose_capture_notebook([first, second], None)
    assert raised.value.candidate_ids == [first, second]


def test_notebook_not_found_has_one_fixed_message() -> None:
    assert str(NotebookNotFoundError()) == NotebookNotFoundError.MESSAGE
    assert NotebookNotFoundError.CODE == "notebook_not_found"


def test_kitchen_archived_error_code() -> None:
    assert KitchenArchivedError.CODE == "kitchen_archived"


def test_notebook_choice_required_error_code() -> None:
    assert NotebookChoiceRequiredError.CODE == "notebook_choice_required"
