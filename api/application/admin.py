"""The read-only dashboard (spec 055 US4).

EXCEPTION to the AGENTS.md rule that every recipe query checks the caller's notebook: the
`/admin/recipes` route reads recipe titles and figures across notebooks the admin does not belong
to. Approved in writing by the project owner on 2026-11-02 and limited to that route; see
specs/055-custom-units/plan.md, Complexity Tracking. It never reads ingredients, steps or
conversations, and the rule stands everywhere else.

Every read checks the caller first, so anyone else gets the same answer as an unknown path.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from domain.errors import AdminNotFoundError

from application.ports import (
    AdminIngredientRow,
    AdminRecipeRow,
    AdminReportRepository,
    AdminUnitRow,
    AdminUserRow,
)


class AdminDashboard:
    def __init__(self, reports: AdminReportRepository) -> None:
        self._reports = reports

    def _require_admin(self, user_id: UUID | None) -> None:
        if user_id is None or not self._reports.is_admin(user_id):
            raise AdminNotFoundError()

    def units(self, user_id: UUID | None) -> Sequence[AdminUnitRow]:
        self._require_admin(user_id)
        return self._reports.units()

    def ingredients(self, user_id: UUID | None) -> Sequence[AdminIngredientRow]:
        self._require_admin(user_id)
        return self._reports.ingredients()

    def recipes(self, user_id: UUID | None) -> Sequence[AdminRecipeRow]:
        self._require_admin(user_id)
        return self._reports.recipes()

    def users(self, user_id: UUID | None) -> Sequence[AdminUserRow]:
        self._require_admin(user_id)
        return self._reports.users()
