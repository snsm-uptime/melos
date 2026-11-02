"""Pure notebook rules (spec 056 FR-001 to FR-011, data-model.md "Domain")."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from domain.errors import (
    InvalidNotebookError,
    InvalidNotebookNameError,
    KitchenArchivedError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
)
from domain.notebook import (
    NOTEBOOK_NAME_MAX_LENGTH,
    JoinedMember,
    Notebook,
    choose_capture_notebook,
    default_notebook_name,
    kitchen_notebook_name,
    longest_standing,
    notebook_access,
    validate_notebook_name,
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


def test_snapshot_key_on_personal_notebook_rejected() -> None:
    with pytest.raises(InvalidNotebookError):
        Notebook(id=uuid4(), name="ana's Notebook", snapshot_key=uuid4())


def test_snapshot_key_on_kitchen_notebook_allowed() -> None:
    key = uuid4()
    assert Notebook(id=uuid4(), name="x", kitchen_id=uuid4(), snapshot_key=key).snapshot_key == key


def test_default_notebook_name_uses_alias_in_the_language() -> None:
    assert default_notebook_name("ana", "en") == "ana's Notebook"
    assert default_notebook_name("ana", "es") == "Cuaderno de ana"


def test_kitchen_notebook_name_uses_alias_and_kitchen_in_the_language() -> None:
    assert kitchen_notebook_name("ana", "Home", "en") == "ana's (Home) Notebook"
    assert kitchen_notebook_name("ana", "Casa", "es") == "Cuaderno de ana (Casa)"


def test_notebook_names_are_spanish_when_no_language_is_saved() -> None:
    assert default_notebook_name("ana", None) == "Cuaderno de ana"
    assert kitchen_notebook_name("ana", "Casa", None) == "Cuaderno de ana (Casa)"


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


def test_a_new_notebook_name_is_trimmed() -> None:
    assert validate_notebook_name("  Postres  ") == "Postres"


@pytest.mark.parametrize("raw", ["", "   ", "x" * (NOTEBOOK_NAME_MAX_LENGTH + 1)])
def test_a_blank_or_long_notebook_name_is_refused(raw: str) -> None:
    with pytest.raises(InvalidNotebookNameError):
        validate_notebook_name(raw)


JOINED = datetime(2026, 3, 1, tzinfo=UTC)


def _member(user_id: UUID, days: int = 0, role: str = "member") -> JoinedMember:
    return JoinedMember(
        user_id=user_id,
        role=role,  # type: ignore[arg-type]
        joined_at=JOINED + timedelta(days=days),
    )


def test_longest_standing_is_the_earliest_to_join() -> None:
    first, second = sorted([uuid4(), uuid4()], reverse=True)
    members = [_member(second, 5), _member(first, 1)]
    assert longest_standing(members) == first


def test_longest_standing_ignores_the_owner() -> None:
    owner, member = uuid4(), uuid4()
    assert longest_standing([_member(owner, -100, "owner"), _member(member)]) == member


@pytest.mark.parametrize("flip", [False, True])
def test_longest_standing_breaks_a_tie_by_id_in_any_input_order(flip: bool) -> None:
    low, high = sorted([uuid4(), uuid4()])
    members = [_member(low), _member(high)]
    assert longest_standing(reversed(members) if flip else members) == low


def test_longest_standing_with_no_members_is_none() -> None:
    assert longest_standing([_member(uuid4(), role="owner")]) is None
    assert longest_standing([]) is None
