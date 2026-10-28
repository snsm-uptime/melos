"""Pure rules for changing a recipe (spec 027): who may write, and the catalog name proposal."""

from __future__ import annotations

import pytest
from domain.ingredient_catalog import propose_entry
from domain.notebook import can_write_recipes


@pytest.mark.parametrize(
    ("access", "archived", "expected"),
    [
        ("owner", None, True),
        ("member", None, True),
        ("kitchen_member", False, True),
        ("kitchen_member", None, True),
        ("kitchen_member", True, False),
    ],
)
def test_who_may_write_recipes(access: str, archived: bool | None, expected: bool) -> None:
    assert can_write_recipes(access, archived) is expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("typed", "catalog", "expected"),
    [
        ("onions", ["onion", "garlic"], "onion"),
        ("tomatoes", ["tomato"], "tomato"),
        ("leaves", ["leaf"], "leaf"),
        ("Onion", ["onion"], "onion"),
        (" onion ", ["onion"], "onion"),
        ("onion", ["onion"], "onion"),
        ("garlic", ["onion"], None),
        ("garlic", [], None),
        ("   ", ["onion"], None),
        ("", ["onion"], None),
    ],
)
def test_propose_entry(typed: str, catalog: list[str], expected: str | None) -> None:
    assert propose_entry(typed, catalog) == expected
