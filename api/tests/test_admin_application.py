"""The dashboard's access rule, against a fake repository (spec 055 FR-017a)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from application.admin import AdminDashboard
from domain.errors import AdminNotFoundError

ADMIN, PERSON = uuid4(), uuid4()


@dataclass
class FakeReports:
    reads: list[str] = field(default_factory=list)

    def is_admin(self, user_id: UUID) -> bool:
        return user_id == ADMIN

    def units(self) -> list:
        self.reads.append("units")
        return []

    def ingredients(self) -> list:
        self.reads.append("ingredients")
        return []

    def recipes(self) -> list:
        self.reads.append("recipes")
        return []

    def users(self) -> list:
        self.reads.append("users")
        return []


SECTIONS = ("units", "ingredients", "recipes", "users")


@pytest.mark.parametrize("section", SECTIONS)
def test_an_admin_reads_each_section(section: str) -> None:
    reports = FakeReports()
    assert getattr(AdminDashboard(reports), section)(ADMIN) == []
    assert reports.reads == [section]


@pytest.mark.parametrize("section", SECTIONS)
@pytest.mark.parametrize("caller", [PERSON, None])
def test_anyone_else_is_refused_before_any_read(section: str, caller: UUID | None) -> None:
    reports = FakeReports()
    with pytest.raises(AdminNotFoundError):
        getattr(AdminDashboard(reports), section)(caller)
    assert reports.reads == []
