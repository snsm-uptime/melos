"""Recipe list rules (spec 021) and meaning search rules (spec 019)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from domain.errors import InvalidPageError, InvalidSearchFiltersError, InvalidSearchQuestionError
from domain.recipe_search import (
    PAGE_SIZE,
    SEARCH_LIMIT,
    SearchFilters,
    clamp_page,
    mark,
    search_key,
    search_question,
)


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


# --- Meaning search (spec 019) ----------------------------------------------------------------


def test_search_limit_is_five() -> None:
    assert SEARCH_LIMIT == 5


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0.9, "close"), (0.65, "close"), (0.6499, "weak"), (-0.2, "weak")],
)
def test_mark_against_the_minimum(score: float, expected: str) -> None:
    assert mark(score, 0.65) == expected


def test_filters_normalize_and_deduplicate_ingredient_names() -> None:
    filters = SearchFilters(ingredient_names=(" Chicken ", "chicken", "LIMÓN", "", "rice"))
    assert filters.ingredient_names == ("chicken", "limon", "rice")


def test_filters_deduplicate_excluded_recipes() -> None:
    first, second = uuid4(), uuid4()
    assert SearchFilters(exclude_recipe_ids=(first, second, first)).exclude_recipe_ids == (
        first,
        second,
    )


def test_created_after_later_than_created_before_is_refused() -> None:
    later = datetime(2026, 11, 2, tzinfo=UTC)
    with pytest.raises(InvalidSearchFiltersError):
        SearchFilters(created_after=later, created_before=later - timedelta(days=1))


def test_equal_dates_are_allowed() -> None:
    day = datetime(2026, 11, 2, tzinfo=UTC)
    assert SearchFilters(created_after=day, created_before=day).created_after == day


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_empty_question_is_refused(question: str) -> None:
    with pytest.raises(InvalidSearchQuestionError):
        search_question(question)


def test_question_is_trimmed() -> None:
    assert search_question("  arroz con pollo  ") == "arroz con pollo"
