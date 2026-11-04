"""PageReader adapters: HTML in, schema.org recipes, main photo address and Markdown out.

`TrafilaturaPageReader` (spec 026, research R6) reads the JSON-LD blocks and og:image with the
stdlib (`adapters/web/jsonld.py`), maps them with `domain.recipe_page.recipes_from_jsonld`,
and turns the page's main content into Markdown with trafilatura, which drops navigation,
headers, footers, comments, forms and ads. trafilatura's own downloader is never called:
the page always comes from the PageFetcher. No network, no file access, never raises.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import trafilatura
from application.ports import PageContent
from domain.recipe_page import PageRecipe, recipes_from_jsonld

from adapters.web.jsonld import read_page_data

logger = logging.getLogger(__name__)
# trafilatura logs page fragments at DEBUG and INFO; page text must not reach the logs (R12).
logging.getLogger("trafilatura").setLevel(logging.WARNING)


class TrafilaturaPageReader:
    def read(self, html: str, base_url: str) -> PageContent:
        if not html or not html.strip():
            return PageContent(recipes=(), main_image_url=None, markdown="")
        data = read_page_data(html)
        recipes = recipes_from_jsonld(data.objects)
        return PageContent(
            recipes=recipes,
            main_image_url=_main_image(recipes, data.og_image, base_url),
            markdown=_markdown(html),
        )


def _markdown(html: str) -> str:
    try:
        text = trafilatura.extract(
            html,
            output_format="markdown",
            include_tables=True,
            include_formatting=True,
            include_comments=False,
            include_images=False,
            include_links=False,
            favor_recall=True,
            # Off on purpose: trafilatura's deduplication keeps a process-wide cache of text it
            # has seen, so after a page is read three times its paragraphs read as repeats and
            # the Markdown comes back empty for the next member. Repeats inside one page are
            # dropped by domain.recipe_page.merge_parts instead.
            deduplicate=False,
        )
    except Exception:  # a parser failure is an unreadable page, not an error
        logger.info("page markdown could not be read")
        return ""
    return (text or "").strip()


def _main_image(recipes: tuple[PageRecipe, ...], og_image: str | None, base_url: str) -> str | None:
    """The single recipe's first image, else og:image; absolute http(s) only."""
    candidates: list[str] = []
    if len(recipes) == 1:
        candidates.extend(recipes[0].image_urls[:1])
    if og_image:
        candidates.append(og_image)
    for candidate in candidates:
        try:
            url = urljoin(base_url, candidate.strip())
            scheme = urlsplit(url).scheme.lower()
        except ValueError:
            continue
        if scheme in ("http", "https"):
            return url
    return None


@dataclass(frozen=True, slots=True)
class FakePageReader:
    """Stand-in PageReader for tests: returns one fixed PageContent."""

    content: PageContent

    def read(self, html: str, base_url: str) -> PageContent:
        return self.content
