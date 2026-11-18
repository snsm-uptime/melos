"""The export use case against fake ports (spec 024): access, closed lists, and no writes."""

from __future__ import annotations

from uuid import uuid4

import pytest
from application.ports import SessionRef
from application.shopping_export import ExportShoppingListService
from domain.errors import KitchenNotFoundError, ShoppingListNotFoundError
from domain.shopping_export import ExportDocument
from tests.test_carts_application import CAT
from tests.test_shopping_list_saved_application import Saved


def export(f: Saved, ref: SessionRef, list_id: object) -> ExportDocument:
    service = ExportShoppingListService(f.s.world.kitchens, f.lists)
    return service.execute(ref, f.s.kitchen, list_id)  # type: ignore[arg-type]


def snapshot(f: Saved) -> tuple[object, ...]:
    return (f.lists.active(f.s.kitchen), f.lists.closed(f.s.kitchen))


def test_a_member_gets_the_document_of_the_active_list() -> None:
    f = Saved()
    f.rice()
    document = export(f, f.s.ana, f.get().list_id)
    assert [line.text for line in document.lines] == ["rice — 2 cup"]
    assert document.lines[0].sources == ("Rice",)


def test_a_closed_list_exports_with_its_closing_date_and_is_unchanged() -> None:
    f = Saved()
    f.rice()
    closed = f.done()
    before = snapshot(f)
    document = export(f, f.s.ana, closed.saved.id)
    assert document.list_date == closed.saved.closing_date
    assert [line.text for line in document.lines] == ["rice — 2 cup"]
    assert snapshot(f) == before


def test_a_non_member_gets_not_found() -> None:
    f = Saved()
    f.rice()
    with pytest.raises(KitchenNotFoundError):
        export(f, SessionRef(CAT, uuid4()), f.get().list_id)


def test_an_unknown_id_gets_not_found() -> None:
    f = Saved()
    f.rice()
    with pytest.raises(ShoppingListNotFoundError):
        export(f, f.s.ana, uuid4())


def test_export_never_writes_to_the_list() -> None:
    f = Saved()
    f.rice()
    before = snapshot(f)
    export(f, f.s.ana, f.get().list_id)
    assert snapshot(f) == before


def test_manual_items_are_in_the_export() -> None:
    f = Saved()
    f.rice()
    f.add("lemon")
    document = export(f, f.s.ana, f.get().list_id)
    assert [(line.text, line.is_manual) for line in document.lines] == [
        ("rice — 2 cup", False),
        ("lemon", True),
    ]
