"""TrafilaturaPageReader on the invented fixture pages (spec 026 T025). No network."""

from __future__ import annotations

from pathlib import Path

import pytest
from adapters.web.jsonld import read_page_data
from adapters.web.page_reader import FakePageReader, TrafilaturaPageReader
from application.ports import PageContent

PAGES = Path(__file__).parent / "fixtures" / "pages"
BASE = "https://example.test/recipes/page"


def _read(name: str, base: str = BASE) -> PageContent:
    html = (PAGES / f"{name}.html").read_text(encoding="utf-8")
    return TrafilaturaPageReader().read(html, base)


def test_a_schema_org_page_gives_one_recipe_and_its_first_image() -> None:
    content = _read("jsonld_recipe")

    (recipe,) = content.recipes
    assert recipe.title == "Golden Lentil Soup"
    assert recipe.yield_text == "4 servings"
    assert len(recipe.ingredients) == 4
    assert recipe.steps == (
        "Rinse the lentils.",
        "Fry the onions in the oil until soft.",
        "Add the lentils and 1 litre of water & simmer for 20 minutes.",
        "Season with salt and serve.",
    )
    # The first JSON-LD image, resolved against the page address; not the og:image.
    assert content.main_image_url == "https://example.test/images/lentil-soup.jpg"


def test_a_plain_page_gives_markdown_without_navigation_footer_ads_or_comments() -> None:
    content = _read("plain_recipe")

    assert content.recipes == ()
    markdown = content.markdown
    assert "- 2 ripe bananas" in markdown
    assert "- a splash of milk" in markdown
    assert "1. Mash the bananas in a bowl with a fork." in markdown
    assert "3. Cook small spoonfuls" in markdown
    for noise in ("menu link", "ADVERT", "COMMENTER TEXT", "FOOTER TEXT"):
        assert noise not in markdown
    # Links keep their text only.
    assert "guide to frying pans" in markdown
    assert "/guides/pans" not in markdown and "](" not in markdown


def test_the_og_image_is_used_when_there_is_no_recipe_image() -> None:
    assert _read("plain_recipe").main_image_url == "https://example.test/media/pancakes.png"


def test_two_recipes_are_both_returned_and_no_photo_is_chosen() -> None:
    content = _read("jsonld_two_recipes")

    assert [recipe.title for recipe in content.recipes] == ["Quick Tomato Pasta", "Garlic Rice"]
    assert content.main_image_url is None


def test_an_image_object_on_a_spanish_page() -> None:
    content = _read("spanish_recipe")

    (recipe,) = content.recipes
    assert recipe.title == "Tortilla de patatas"
    assert content.main_image_url == "https://cocina.example.test/fotos/tortilla.webp"


def test_a_script_only_page_has_no_text_and_no_recipe() -> None:
    content = _read("script_only")

    assert content == PageContent(recipes=(), main_image_url=None, markdown="")


def test_reading_the_same_page_many_times_gives_the_same_markdown() -> None:
    # trafilatura's own deduplication caches text across calls and empties a page read often.
    first = _read("plain_recipe").markdown

    assert first
    assert all(_read("plain_recipe").markdown == first for _ in range(6))


def test_a_long_blog_page_keeps_all_of_its_text() -> None:
    markdown = _read("long_blog").markdown

    assert len(markdown) > 25_000
    assert markdown.index("500 g dried white beans") < markdown.index("Soak the beans")


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<<<>>>",
        "<html><body><p>unclosed <b>tags <script type='application/ld+json'>{bad",
        '<script type="application/ld+json">{"@type": "Recipe", "name": </script>',
        "\x00\x01\x02 binary-ish",
    ],
)
def test_bad_html_never_raises(html: str) -> None:
    content = TrafilaturaPageReader().read(html, BASE)

    assert isinstance(content, PageContent)
    assert content.recipes == ()


def test_jsonld_type_is_compared_case_insensitively_and_ignores_parameters() -> None:
    html = (
        '<script type="Application/LD+JSON; charset=utf-8">{"@type": "Recipe", "name": "A"}'
        "</script>"
        '<script type="application/json">{"@type": "Recipe", "name": "Not LD"}</script>'
        '<meta property="og:image" content=" /first.jpg ">'
        '<meta property="og:image" content="/second.jpg">'
    )

    data = read_page_data(html)

    assert data.objects == ({"@type": "Recipe", "name": "A"},)
    assert data.og_image == "/first.jpg"


def test_an_unsafe_photo_address_is_left_for_the_fetcher_to_refuse() -> None:
    html = '<meta property="og:image" content="javascript:alert(1)">'

    assert TrafilaturaPageReader().read(html, BASE).main_image_url is None


def test_the_fake_reader_returns_its_content() -> None:
    content = PageContent(recipes=(), main_image_url=None, markdown="# Soup")

    assert FakePageReader(content).read("<html/>", BASE) == content
