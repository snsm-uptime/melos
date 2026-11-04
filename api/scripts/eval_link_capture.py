"""Manual AI evaluation for link capture (spec 026 SC-006). Needs GEMINI_API_KEY; no database.

Reads every invented page in tests/fixtures/ai_eval/pages/ through FakePageFetcher (the address
checks refuse pages served from this machine), the real TrafilaturaPageReader and the real
Gemini extractor, and prints each draft for scoring against CASES.md:

    docker compose exec api uv run python -m scripts.eval_link_capture
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from adapters.llm.gemini_extractor import GeminiRecipeExtractor
from adapters.web.fake_page_fetcher import FakePageFetcher
from adapters.web.page_reader import TrafilaturaPageReader
from api.settings import (
    load_gemini_settings,
    load_recipe_page_batch_chars,
    load_recipe_page_max_batches,
)
from application.ports import FetchedPage, NotebookFacts
from application.recipe_capture_url import (
    CapturedPageDraft,
    CaptureRecipeUrl,
    CaptureRecipeUrlCommand,
)
from application.recipe_extraction import RecipeExtraction
from domain.notebook import Notebook

PAGES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "ai_eval" / "pages"
BASE = "https://eval.example.test/"


@dataclass
class _Notebooks:
    facts: dict[UUID, NotebookFacts] = field(default_factory=dict)

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        return self.facts.get(notebook_id)


class _Catalog:
    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        return []


class _Units:
    def extras_for(self, user_id: UUID) -> list[str]:
        return []


def main() -> int:
    settings = load_gemini_settings()
    files = sorted(PAGES.glob("*.html"))
    pages = {}
    for path in files:
        html = path.read_text(encoding="utf-8")
        pages[BASE + path.name] = FetchedPage(BASE + path.name, html, len(html.encode()))
    notebook_id = uuid4()
    notebooks = _Notebooks(
        {
            notebook_id: NotebookFacts(
                notebook=Notebook(id=notebook_id, name="Eval"),
                role="owner",
                in_kitchen=False,
                owner_alias="eval",
                kitchen_is_archived=None,
                is_default=True,
                recipe_count=0,
            )
        }
    )
    capture = CaptureRecipeUrl(
        notebooks,
        _Catalog(),
        RecipeExtraction(
            GeminiRecipeExtractor(api_key=settings.api_key, model=settings.chat_model)
        ),
        FakePageFetcher(pages=pages),
        TrafilaturaPageReader(),
        units=_Units(),
        timeout_s=settings.text_timeout_s,
        batch_chars=load_recipe_page_batch_chars(),
        max_batches=load_recipe_page_max_batches(),
    )
    for path in files:
        started = time.monotonic()
        result = capture.execute(
            CaptureRecipeUrlCommand(uuid4(), notebook_id, BASE + path.name, "en")
        )
        elapsed = time.monotonic() - started
        print(f"== {path.name} ({elapsed:.1f}s)")
        if not isinstance(result, CapturedPageDraft):
            problems = getattr(result, "problems", None)
            detail: object = result
            if problems:
                kinds = [(p.name, p.kind.value) for p in problems.line_problems]
                detail = (problems.missing, kinds)
            print("   outcome:", type(result).__name__, detail)
            continue
        recipe = result.recipe
        print(f"   title: {recipe.title!r}  servings: {recipe.base_servings}", end="")
        print(" (estimated)" if recipe.servings_estimated else "")
        for line in recipe.ingredient_lines:
            amount = "vague" if line.vague else f"{line.quantity} {line.unit}"
            preparation = f" [{line.preparation}]" if line.preparation else ""
            print(f"   - {amount} {line.name}{preparation}")
        print(f"   steps: {len(recipe.steps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
