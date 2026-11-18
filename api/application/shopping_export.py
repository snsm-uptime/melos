"""The shopping list export use case (spec 024): reads one saved list and builds its document.

Any list of the kitchen can be exported, active or closed (spec 024 clarification). A member who
cannot read the kitchen, and an unknown list ID, both get ShoppingListNotFoundError, so the two
cannot be told apart (FR-013). The export reads stored lines only, never the cart draft, and never
writes (FR-009, FR-012).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID

from domain.errors import ShoppingListNotFoundError
from domain.shopping_export import ExportDocument, Locale, build_export_document
from domain.shopping_list import SavedList, line_names, shown_list_name

from application.kitchens import KitchenRepository
from application.ports import PreferencesRepository, SessionRef, ShoppingListRepository
from application.shopping_list import _member_kitchen, viewer_language

# The interface language when the member has none saved (spec 063).
DEFAULT_LOCALE: Locale = "es"


class ExportShoppingListService:
    def __init__(
        self,
        kitchens: KitchenRepository,
        lists: ShoppingListRepository,
        *,
        prefs: PreferencesRepository | None = None,
    ) -> None:
        self._kitchens = kitchens
        self._lists = lists
        self._prefs = prefs

    def execute(self, ref: SessionRef, kitchen_id: UUID, list_id: UUID) -> ExportDocument:
        _member_kitchen(self._kitchens, ref, kitchen_id)
        saved = self._saved(kitchen_id, list_id)
        language = viewer_language(self._prefs, ref.user_id)
        names = line_names(saved.items)
        # Each line in the viewer's own word for the ingredient (spec 043 FR-007).
        items = tuple(
            replace(item, name=shown_list_name(item.name, names, language)) for item in saved.items
        )
        locale: Locale = language or DEFAULT_LOCALE  # type: ignore[assignment]
        return build_export_document(items, self._list_date(saved), locale)

    def _saved(self, kitchen_id: UUID, list_id: UUID) -> SavedList:
        active = self._lists.active(kitchen_id)
        if active is not None and active.id == list_id:
            return active
        closed = self._lists.closed_by_id(kitchen_id, list_id)
        if closed is None:
            raise ShoppingListNotFoundError()
        return closed

    @staticmethod
    def _list_date(saved: SavedList) -> date:
        """The closing date, or today (UTC) for an active list."""
        return saved.closing_date or datetime.now(UTC).date()
