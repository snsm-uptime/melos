"""Recipes read from web pages: JSON-LD mapping, splitting, merging (spec 026 T019 to T022)."""

from __future__ import annotations

import pytest
from domain.recipe_draft import DraftRecipe, IngredientLine
from domain.recipe_page import (
    DraftPart,
    MultipleRecipes,
    NoRecipeContent,
    PageRecipe,
    apply_page_recipe,
    markdown_from,
    merge_parts,
    parse_yield,
    recipes_from_jsonld,
    split_markdown,
)

# --- T019: JSON-LD mapping ---


def _recipe(**fields) -> dict:
    return {"@type": "Recipe", "name": "Lentil soup", **fields}


def test_finds_a_recipe_in_a_plain_object() -> None:
    (recipe,) = recipes_from_jsonld([_recipe()])

    assert recipe.title == "Lentil soup"


def test_finds_recipes_in_a_list_and_in_a_graph() -> None:
    objects = [
        [_recipe(name="A"), {"@type": "Person", "name": "Not a recipe"}],
        {"@context": "https://schema.org", "@graph": [{"@type": "WebPage"}, _recipe(name="B")]},
    ]

    assert [recipe.title for recipe in recipes_from_jsonld(objects)] == ["A", "B"]


def test_finds_a_recipe_typed_with_a_list_and_inside_main_entity() -> None:
    objects = [
        {"@type": ["Recipe", "NewsArticle"], "name": "Typed twice"},
        {"@type": "WebPage", "mainEntity": _recipe(name="Main")},
    ]

    assert [recipe.title for recipe in recipes_from_jsonld(objects)] == ["Typed twice", "Main"]


def test_ignores_other_types_and_values() -> None:
    objects = [{"@type": "Article", "name": "News"}, "text", 4, None, {"@type": "HowTo"}]

    assert recipes_from_jsonld(objects) == ()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("4 servings", "4 servings"), (6, "6"), (["8", "8 portions"], "8"), (None, None)],
)
def test_maps_the_yield_as_text(value, expected) -> None:
    (recipe,) = recipes_from_jsonld([_recipe(recipeYield=value)])

    assert recipe.yield_text == expected


def test_maps_ingredients_and_strips_tags_and_entities() -> None:
    (recipe,) = recipes_from_jsonld(
        [_recipe(recipeIngredient=["1 cup <b>red</b> lentils", "salt &amp; pepper", "  ", 3])]
    )

    assert recipe.ingredients == ("1 cup red lentils", "salt & pepper")


def test_instructions_as_one_string_with_line_breaks() -> None:
    (recipe,) = recipes_from_jsonld(
        [_recipe(recipeInstructions="Rinse the lentils.\nBoil them.<br>Serve.\n\n")]
    )

    assert recipe.steps == ("Rinse the lentils.", "Boil them.", "Serve.")


def test_instructions_as_a_list_of_strings_and_steps() -> None:
    (recipe,) = recipes_from_jsonld(
        [
            _recipe(
                recipeInstructions=[
                    "Rinse.",
                    {"@type": "HowToStep", "text": "Boil &amp; stir."},
                    {"@type": "HowToStep", "name": "Serve."},
                    {"@type": "HowToStep"},
                ]
            )
        ]
    )

    assert recipe.steps == ("Rinse.", "Boil & stir.", "Serve.")


def test_sections_are_flattened_in_order() -> None:
    (recipe,) = recipes_from_jsonld(
        [
            _recipe(
                recipeInstructions=[
                    {
                        "@type": "HowToSection",
                        "name": "Sauce",
                        "itemListElement": [
                            {"@type": "HowToStep", "text": "Fry the garlic."},
                            {"@type": "HowToStep", "text": "Add the tomato."},
                        ],
                    },
                    {
                        "@type": "HowToSection",
                        "name": "Pasta",
                        "itemListElement": [{"@type": "HowToStep", "text": "Boil the pasta."}],
                    },
                ]
            )
        ]
    )

    assert recipe.steps == ("Fry the garlic.", "Add the tomato.", "Boil the pasta.")


@pytest.mark.parametrize(
    ("image", "expected"),
    [
        ("https://example.test/a.jpg", ("https://example.test/a.jpg",)),
        (["/a.jpg", "/b.jpg"], ("/a.jpg", "/b.jpg")),
        ({"@type": "ImageObject", "url": "/c.webp"}, ("/c.webp",)),
        ([{"@type": "ImageObject", "url": "/d.png"}, "/e.png"], ("/d.png", "/e.png")),
        (None, ()),
    ],
)
def test_maps_images(image, expected) -> None:
    (recipe,) = recipes_from_jsonld([_recipe(image=image)])

    assert recipe.image_urls == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4 servings", 4),
        ("Serves 4", 4),
        ("4-6", 4),
        ("4 porciones", 4),
        (6, 6),
        ("6", 6),
        ("a crowd", None),
        ("0", None),
        (None, None),
        ("", None),
    ],
)
def test_parse_yield(text, expected) -> None:
    assert parse_yield(text) == expected


# --- T020: splitting ---


def test_text_under_the_limit_is_one_batch() -> None:
    result = split_markdown("# Soup\n\n- 1 onion\n\n1. Fry.", batch_chars=1000, max_batches=4)

    assert result.batches == ("# Soup\n\n- 1 onion\n\n1. Fry.",)
    assert result.cut is False


def test_empty_markdown_gives_no_batch() -> None:
    assert split_markdown("  \n\n ", batch_chars=1000, max_batches=4).batches == ()


def test_splits_on_blank_lines_and_keeps_page_order() -> None:
    blocks = [f"Block {index} " + "x" * 80 for index in range(10)]
    markdown = "\n\n".join(blocks)

    result = split_markdown(markdown, batch_chars=200, max_batches=10)

    assert len(result.batches) == 5
    assert "\n\n".join(result.batches) == markdown
    assert all(len(batch) <= 200 for batch in result.batches)
    assert result.cut is False


def test_an_over_long_block_splits_on_line_breaks_never_inside_a_line() -> None:
    lines = [f"- ingredient {index} " + "y" * 40 for index in range(20)]
    block = "\n".join(lines)

    result = split_markdown(block, batch_chars=200, max_batches=20)

    assert len(result.batches) > 1
    assert all(len(batch) <= 200 for batch in result.batches)
    rebuilt = [line for batch in result.batches for line in batch.split("\n")]
    assert rebuilt == lines


def test_a_single_line_longer_than_a_batch_is_cut_at_a_space() -> None:
    words = [f"word{index}" for index in range(100)]
    line = " ".join(words)

    result = split_markdown(line, batch_chars=100, max_batches=50)

    assert all(len(batch) <= 100 for batch in result.batches)
    assert " ".join(result.batches).split(" ") == words


def test_lines_after_a_cut_line_stay_on_their_own_line() -> None:
    long_line = " ".join(f"w{index}" for index in range(60))
    block = "- first\n" + long_line + "\n- after"

    result = split_markdown(block, batch_chars=100, max_batches=50)

    joined = "\n".join(result.batches)
    assert joined.startswith("- first\n")
    assert joined.endswith("\n- after")
    assert all(len(batch) <= 100 for batch in result.batches)


def test_more_batches_than_the_cap_are_cut() -> None:
    markdown = "\n\n".join(f"Block {index} " + "z" * 90 for index in range(10))

    result = split_markdown(markdown, batch_chars=100, max_batches=3)

    assert len(result.batches) == 3
    assert result.cut is True
    assert result.batches[0].startswith("Block 0 ")


# --- T021: merging (SC-009) ---


def _line(name: str, quantity: float | None = 1, unit: str | None = "unit", **more):
    return IngredientLine(name=name, vague=quantity is None, quantity=quantity, unit=unit, **more)


def _part(title=None, servings=None, lines=(), steps=()) -> DraftPart:
    return DraftPart(
        title=title, base_servings=servings, ingredient_lines=tuple(lines), steps=tuple(steps)
    )


def test_merge_takes_title_and_servings_from_the_first_part_that_has_them() -> None:
    merged = merge_parts(
        [
            _part(lines=[_line("onion")]),
            _part(title="Bean stew", servings=None),
            _part(title="Bean stew", servings=6, steps=["Simmer."]),
        ]
    )

    assert isinstance(merged, DraftRecipe)
    assert merged.title == "Bean stew"
    assert merged.base_servings == 6


def test_ingredients_early_and_steps_late_make_one_draft() -> None:
    merged = merge_parts(
        [
            _part(title="Bean stew", lines=[_line("bean", 500, "gram"), _line("onion")]),
            NoRecipeContent(),
            _part(steps=["Soak the beans.", "Simmer for two hours."]),
        ]
    )

    assert isinstance(merged, DraftRecipe)
    assert [line.name for line in merged.ingredient_lines] == ["bean", "onion"]
    assert merged.steps == ("Soak the beans.", "Simmer for two hours.")


def test_lines_and_steps_keep_batch_order_and_drop_repeats() -> None:
    merged = merge_parts(
        [
            _part(
                title="Stew",
                lines=[_line("onion", preparation="chopped"), _line("salt", None, None)],
            ),
            _part(
                lines=[
                    _line(" Onion ", preparation="Chopped "),
                    _line("carrot"),
                    _line("salt", None, None),
                    _line("onion", 2),
                ],
                steps=["Fry  the onion.", "Add the carrot."],
            ),
            _part(steps=["Fry the onion.", "Serve."]),
        ]
    )

    assert isinstance(merged, DraftRecipe)
    assert [(line.name, line.quantity) for line in merged.ingredient_lines] == [
        ("onion", 1),
        ("salt", None),
        ("carrot", 1),
        ("onion", 2),
    ]
    assert merged.steps == ("Fry  the onion.", "Add the carrot.", "Serve.")


def test_a_part_with_two_recipes_makes_the_page_multiple() -> None:
    assert merge_parts([_part(title="A", steps=["x"]), MultipleRecipes()]) == MultipleRecipes()


def test_two_complete_parts_with_different_titles_are_multiple() -> None:
    first = _part(title="Tomato pasta", lines=[_line("pasta")], steps=["Boil."])
    second = _part(title="Garlic rice", lines=[_line("rice")], steps=["Fry."])

    assert merge_parts([first, second]) == MultipleRecipes()


def test_the_printable_card_repeat_is_one_recipe() -> None:
    first = _part(title="Bean Stew", lines=[_line("bean")], steps=["Simmer."])
    card = _part(title="  bean   stéw ", lines=[_line("bean")], steps=["Simmer."])
    labelled = _part(title="Bean stew (printable card)", lines=[_line("bean")], steps=["Simmer."])

    merged = merge_parts([first, card, labelled])

    assert isinstance(merged, DraftRecipe)
    assert merged.title == "Bean Stew"
    assert len(merged.ingredient_lines) == 1
    assert merged.steps == ("Simmer.",)


def test_every_part_empty_is_no_recipe_content() -> None:
    assert merge_parts([NoRecipeContent(), NoRecipeContent()]) == NoRecipeContent()
    assert merge_parts([]) == NoRecipeContent()


def test_a_merged_draft_without_title_or_steps_is_returned_raw_for_check_draft() -> None:
    merged = merge_parts([_part(lines=[_line("onion")])])

    assert isinstance(merged, DraftRecipe)
    assert merged.title == ""
    assert merged.steps == ()


# --- T022: schema.org text and overrides ---

PAGE = PageRecipe(
    title="Golden Lentil Soup",
    yield_text="4 servings",
    ingredients=("1 cup red lentils", "2 large onions, chopped"),
    steps=("Rinse the lentils.", "Simmer for 20 minutes."),
    image_urls=("/a.jpg",),
)


def test_markdown_from_a_page_recipe() -> None:
    assert markdown_from(PAGE) == (
        "# Golden Lentil Soup\n\n"
        "Servings: 4 servings\n\n"
        "## Ingredients\n\n"
        "- 1 cup red lentils\n"
        "- 2 large onions, chopped\n\n"
        "## Steps\n\n"
        "1. Rinse the lentils.\n"
        "2. Simmer for 20 minutes."
    )


def test_markdown_from_leaves_out_missing_parts() -> None:
    bare = PageRecipe(title=None, yield_text=None, ingredients=("1 egg",), steps=(), image_urls=())

    assert markdown_from(bare) == "## Ingredients\n\n- 1 egg"


def _model_draft(**overrides) -> DraftRecipe:
    values = {
        "title": "Lentil soup",
        "base_servings": 2,
        "servings_estimated": True,
        "ingredient_lines": (_line("lentil", 1, "cup"),),
        "steps": ("Rinse.", "Simmer."),
    }
    return DraftRecipe(**(values | overrides))


def test_apply_page_recipe_replaces_title_steps_and_servings() -> None:
    applied = apply_page_recipe(_model_draft(), PAGE)

    assert applied.title == "Golden Lentil Soup"
    assert applied.steps == PAGE.steps
    assert applied.base_servings == 4
    assert applied.servings_estimated is False
    assert applied.ingredient_lines == _model_draft().ingredient_lines


def test_apply_page_recipe_keeps_the_model_servings_without_a_number() -> None:
    page = PageRecipe("Soup", "a crowd", ("1 egg",), ("Boil.",), ())

    applied = apply_page_recipe(_model_draft(), page)

    assert (applied.base_servings, applied.servings_estimated) == (2, True)


def test_apply_page_recipe_keeps_the_model_title_and_steps_when_the_page_has_none() -> None:
    page = PageRecipe(None, None, ("1 egg",), (), ())

    applied = apply_page_recipe(_model_draft(), page)

    assert applied.title == "Lentil soup"
    assert applied.steps == ("Rinse.", "Simmer.")
