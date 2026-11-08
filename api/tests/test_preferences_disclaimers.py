"""The "disclaimers" account option, application level (spec 041, disclaimers-preference)."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from application.ports import UserPreferencesRecord
from application.preferences import (
    GetMePreferencesCommand,
    GetMePreferencesService,
    UpdatePreferencesCommand,
    UpdatePreferencesService,
)


class _Repo:
    def __init__(self, row: UserPreferencesRecord) -> None:
        self.row = row
        self.writes = 0

    def get_preferences(self, user_id):  # noqa: ANN001
        return self.row if user_id == self.row.id else None

    def update_preferences(self, user_id, **kwargs):  # noqa: ANN001, ANN003
        self.writes += 1
        if kwargs.get("disclaimers") is not None:
            self.row = replace(self.row, disclaimers=kwargs["disclaimers"])
        if kwargs.get("language") is not None:
            self.row = replace(self.row, language=kwargs["language"])
        return self.row


def _row(**overrides) -> UserPreferencesRecord:
    fields = {"id": uuid4(), "email": "ana@example.com", "language": None, "theme": None}
    fields.update(overrides)
    return UserPreferencesRecord(**fields)


def test_an_account_that_never_changed_it_shows_the_disclaimer() -> None:
    row = _row()
    repo = _Repo(row)
    result = GetMePreferencesService(repo).execute(GetMePreferencesCommand(user_id=row.id))
    assert result.disclaimers is True


def test_turning_it_off_stores_and_returns_false() -> None:
    row = _row()
    repo = _Repo(row)
    result = UpdatePreferencesService(repo).execute(
        UpdatePreferencesCommand(user_id=row.id, disclaimers=False)
    )
    assert result.disclaimers is False
    assert repo.row.disclaimers is False


def test_none_leaves_the_stored_value_unchanged() -> None:
    row = _row(disclaimers=False)
    repo = _Repo(row)
    result = UpdatePreferencesService(repo).execute(
        UpdatePreferencesCommand(user_id=row.id, language="es", disclaimers=None)
    )
    assert result.disclaimers is False


def test_an_empty_command_returns_the_current_record_without_a_write() -> None:
    row = _row(disclaimers=False)
    repo = _Repo(row)
    result = UpdatePreferencesService(repo).execute(UpdatePreferencesCommand(user_id=row.id))
    assert result.disclaimers is False
    assert repo.writes == 0
