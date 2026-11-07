"""The text a recipe is embedded from (spec 019 FR-022, research R8)."""

from __future__ import annotations

from dataclasses import dataclass

from domain.embed_text import STRATEGIES, plain, toon


@dataclass(frozen=True)
class Line:
    name: str
    vague: bool = False
    quantity: float | None = None
    unit: str | None = None
    size: str | None = None
    preparation: str | None = None
    vague_text: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Recipe:
    title: str
    base_servings: int
    lines: tuple[Line, ...]
    steps: tuple[str, ...]


TOMATO_RICE = Recipe(
    title="tomato rice",
    base_servings=4,
    lines=(
        Line("rice", quantity=1.0, unit="cup"),
        Line("tomato", quantity=2.0, unit="unit", size="large", preparation="grated"),
        Line("garlic", quantity=2.0, unit="unit", preparation="minced"),
        Line("salt", vague=True, vague_text="to taste"),
    ),
    steps=(
        "Fry the garlic in oil.",
        "Add the tomato and cook 5 minutes.",
        "Add the rice and 2 cups of water; cook 18 minutes.",
    ),
)


def test_toon_is_the_b3_shape_without_id() -> None:
    assert toon(TOMATO_RICE) == "\n".join(
        [
            "title: tomato rice",
            "base_servings: 4",
            "ingredients[4]{name,quantity,unit,size,preparation,vague_text,note}:",
            "  rice,1,cup,null,null,null,null",
            "  tomato,2,unit,large,grated,null,null",
            "  garlic,2,unit,null,minced,null,null",
            "  salt,null,null,null,null,to taste,null",
            "steps[3]: Fry the garlic in oil.,Add the tomato and cook 5 minutes.,Add the rice and 2"
            " cups of water; cook 18 minutes.",
        ]
    )
    assert "id:" not in toon(TOMATO_RICE)


def test_toon_keeps_fractions() -> None:
    recipe = Recipe("x", 1, (Line("flour", quantity=0.5, unit="cup"),), ())
    assert "flour,0.5,cup" in toon(recipe)


def test_plain_lists_title_servings_lines_and_steps() -> None:
    assert plain(TOMATO_RICE) == "\n".join(
        [
            "tomato rice",
            "Serves 4.",
            "Ingredients:",
            "- 1 cup rice",
            "- 2 unit large tomato, grated",
            "- 2 unit garlic, minced",
            "- salt (to taste)",
            "Steps:",
            "1. Fry the garlic in oil.",
            "2. Add the tomato and cook 5 minutes.",
            "3. Add the rice and 2 cups of water; cook 18 minutes.",
        ]
    )


def test_both_put_title_and_ingredients_before_the_steps() -> None:
    for render in STRATEGIES.values():
        text = render(TOMATO_RICE)
        assert text.index("tomato rice") < text.index("garlic") < text.index("Fry the garlic")


def test_no_steps_and_a_vague_only_line_render() -> None:
    recipe = Recipe("salad", 2, (Line("salt", vague=True, vague_text="a pinch"),), ())
    for render in STRATEGIES.values():
        text = render(recipe)
        assert "salad" in text and "a pinch" in text


def test_strategy_names() -> None:
    assert set(STRATEGIES) == {"toon", "plain"}
