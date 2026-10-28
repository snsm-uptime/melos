"""Recipe list rules: filter key and page window (spec 021)."""

import pytest
from domain.errors import InvalidPageError
from domain.recipe_search import PAGE_SIZE, clamp_page, search_key


def test_search_key_drops_accents_case_and_extra_spaces() -> None:
    assert search_key("  Calabazá  ") == "calabaza"
    assert search_key("LENTIL   Soup") == "lentil soup"


def test_search_key_blank_is_empty() -> None:
    assert search_key("   ") == ""
    assert search_key("") == ""


@pytest.mark.parametrize(
    ("requested", "total", "expected"),
    [
        (1, 0, (1, 1)),
        (1, 12, (1, 1)),
        (1, 13, (1, 2)),
        (9, 13, (2, 2)),
        (2, 24, (2, 2)),
        (3, 24, (2, 2)),
    ],
)
def test_clamp_page(requested: int, total: int, expected: tuple[int, int]) -> None:
    assert clamp_page(requested, total) == expected


def test_page_size_is_twelve() -> None:
    assert PAGE_SIZE == 12


@pytest.mark.parametrize("requested", [0, -1])
def test_clamp_page_rejects_below_one(requested: int) -> None:
    with pytest.raises(InvalidPageError):
        clamp_page(requested, 5)
