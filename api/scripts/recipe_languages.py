"""Operator command: propose a language for recipes saved before spec 043 (FR-005a).

Run once after deploy, inside the api container:

    docker compose exec api uv run python -m scripts.recipe_languages <subcommand>

| Subcommand | Does |
|---|---|
| detect [--limit N] | ask the model once per recipe not read yet; store a differing proposal |
| status | how many recipes are read, waiting, and have a proposal |

`detect` never changes a recipe's language. When the model's answer differs from the stored
(fallback) language it is stored in `proposed_language`, and the recipe page offers to apply it
(constitution 5). Every recipe it reads gets `language_detected_at`, unsure answers included, so
running it again only reads recipes it has not seen. Only title, ingredient names and steps are
sent. Prints counts, exits 0, or 1 on a database error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from adapters.persistence.db import get_session_factory
from adapters.persistence.models import RecipeIngredientModel, RecipeModel, StepModel
from api.settings import load_gemini_settings
from application.ports import LanguageDetector
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

BATCH = 50
MAX_TEXT_CHARS = 4000


def recipe_text(session: Session, recipe_id: UUID, title: str) -> str:
    names = session.scalars(
        select(RecipeIngredientModel.name)
        .where(RecipeIngredientModel.recipe_id == recipe_id)
        .order_by(RecipeIngredientModel.position)
    ).all()
    steps = session.scalars(
        select(StepModel.text).where(StepModel.recipe_id == recipe_id).order_by(StepModel.position)
    ).all()
    text = "\n".join([title, "", *names, "", *steps])
    return text[:MAX_TEXT_CHARS]


def detect(
    session: Session,
    detector: LanguageDetector,
    limit: int | None = None,
    *,
    only: Sequence[UUID] | None = None,
) -> list[str]:
    """Read recipes not read yet; `only` narrows them to some ids (tests)."""
    read = proposed = unsure = 0
    while limit is None or read < limit:
        size = BATCH if limit is None else min(BATCH, limit - read)
        query = select(RecipeModel.id, RecipeModel.title, RecipeModel.language).where(
            RecipeModel.language_detected_at.is_(None)
        )
        if only is not None:
            query = query.where(RecipeModel.id.in_(list(only)))
        rows = session.execute(
            query.order_by(RecipeModel.created_at, RecipeModel.id).limit(size)
        ).all()
        if not rows:
            break
        for recipe_id, title, stored in rows:
            found = detector.detect(recipe_text(session, recipe_id, title))
            values: dict[str, object] = {"language_detected_at": datetime.now(UTC)}
            if found is None:
                unsure += 1
            elif found != stored:
                values["proposed_language"] = found
                proposed += 1
            session.execute(update(RecipeModel).where(RecipeModel.id == recipe_id).values(values))
            read += 1
        # One commit per batch: a stopped run keeps what it read and resumes from there.
        session.commit()
    return [f"read={read}", f"proposed={proposed}", f"unsure={unsure}"]


def status(session: Session) -> list[str]:
    total = session.scalar(select(func.count()).select_from(RecipeModel)) or 0
    waiting = (
        session.scalar(
            select(func.count())
            .select_from(RecipeModel)
            .where(RecipeModel.language_detected_at.is_(None))
        )
        or 0
    )
    proposals = (
        session.scalar(
            select(func.count())
            .select_from(RecipeModel)
            .where(RecipeModel.proposed_language.is_not(None))
        )
        or 0
    )
    return [f"read={total - waiting}", f"waiting={waiting}", f"proposals={proposals}"]


def _detector() -> LanguageDetector:
    from adapters.llm.gemini_language_detector import GeminiLanguageDetector

    settings = load_gemini_settings()
    return GeminiLanguageDetector(
        api_key=settings.api_key, model=settings.chat_model, timeout_s=settings.text_timeout_s
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.recipe_languages")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("detect", help="propose a language for recipes not read yet")
    run.add_argument("--limit", type=int, default=None)
    sub.add_parser("status", help="read, waiting and proposal counts")
    return parser


def main(argv: Sequence[str] | None = None, detector: LanguageDetector | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "detect" and args.limit is not None and args.limit < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 2
    try:
        with get_session_factory()() as session:
            if args.command == "detect":
                lines = detect(session, detector or _detector(), args.limit)
            else:
                lines = status(session)
    except SQLAlchemyError as exc:
        print(f"database error: {type(exc).__name__}", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
