"""Embedding jobs and recipe embeddings in Postgres (spec 019, research R4, R5, R7, R10).

The job table is the worker's queue. Claims use `FOR UPDATE SKIP LOCKED` and a lease, so two
processes never take the same recipe and a process that dies releases its jobs. An embedding is
written only if the recipe still has the version that was read, and only current embeddings are
searched, so an edited recipe is never found by its old content.

A job is ended (or failed) only while it is still claimed: an edit's enqueue clears the claim,
so a worker that finishes the old content cannot drop the job for the new one.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from application.ports import Backlog, ClaimedJob, RawHit, RecipeDetail
from domain.recipe_search import SearchFilters
from sqlalchemy import text
from sqlalchemy.orm import Session

from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.vector import to_vector_text

_RESET = """
    due_at = now(), attempts = 0, last_wait_s = NULL, claimed_until = NULL, last_failure = NULL
"""


class SqlAlchemyEmbeddingJobs:
    def __init__(self, session: Session) -> None:
        self._session = session

    def enqueue(self, recipe_ids: Sequence[UUID]) -> None:
        if not recipe_ids:
            return
        self._session.execute(
            text(
                f"""
                INSERT INTO embedding_job (recipe_id)
                SELECT unnest(CAST(:ids AS uuid[]))
                ON CONFLICT (recipe_id) DO UPDATE SET {_RESET}
                """
            ),
            {"ids": list(dict.fromkeys(recipe_ids))},
        )

    def enqueue_notebook(self, notebook_id: UUID) -> None:
        self._session.execute(
            text(
                f"""
                INSERT INTO embedding_job (recipe_id)
                SELECT id FROM recipe WHERE notebook_id = :notebook_id
                ON CONFLICT (recipe_id) DO UPDATE SET {_RESET}
                """
            ),
            {"notebook_id": notebook_id},
        )

    def enqueue_missing(self, model: str, *, other_strategy_of: str | None = None) -> int:
        strategy_rule = "AND e.strategy_used = :strategy" if other_strategy_of else ""
        # A job already waiting keeps its attempts and last wait, but is due now: a restart or
        # the command makes a healed service catch up sooner (SC-003). Only new rows count.
        queued = self._session.execute(
            text(
                f"""
                WITH queued AS (
                    INSERT INTO embedding_job (recipe_id)
                    SELECT r.id FROM recipe r
                    WHERE NOT EXISTS (
                        SELECT 1 FROM recipe_embedding e
                        WHERE e.recipe_id = r.id
                          AND e.model = :model
                          AND e.recipe_updated_at = r.updated_at
                          {strategy_rule}
                    )
                    ON CONFLICT (recipe_id) DO UPDATE SET due_at = now()
                    WHERE embedding_job.due_at > now()
                    RETURNING (xmax = 0) AS inserted
                )
                SELECT count(*) FILTER (WHERE inserted) FROM queued
                """
            ),
            {"model": model, "strategy": other_strategy_of},
        ).scalar_one()
        return int(queued)

    def claim(self, batch: int, lease_s: float) -> list[ClaimedJob]:
        rows = self._session.execute(
            text(
                """
                WITH due AS (
                    SELECT recipe_id FROM embedding_job
                    WHERE due_at <= now()
                      AND (claimed_until IS NULL OR claimed_until < now())
                    ORDER BY due_at
                    LIMIT :batch
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE embedding_job j
                SET claimed_until = now() + make_interval(secs => :lease)
                FROM due WHERE j.recipe_id = due.recipe_id
                RETURNING j.recipe_id, j.attempts, j.last_wait_s, j.due_at
                """
            ),
            {"batch": batch, "lease": float(lease_s)},
        ).all()
        rows = sorted(rows, key=lambda row: row.due_at)
        return [ClaimedJob(row.recipe_id, row.attempts, row.last_wait_s) for row in rows]

    def fail(self, recipe_id: UUID, wait_s: float, failure: str) -> None:
        self._session.execute(
            text(
                """
                UPDATE embedding_job
                SET attempts = attempts + 1,
                    last_wait_s = :wait,
                    last_failure = :failure,
                    claimed_until = NULL,
                    due_at = now() + make_interval(secs => :wait)
                WHERE recipe_id = :recipe_id AND claimed_until IS NOT NULL
                """
            ),
            {"recipe_id": recipe_id, "wait": float(wait_s), "failure": failure},
        )

    def release_changed(self, recipe_id: UUID) -> None:
        self._session.execute(
            text(
                """
                UPDATE embedding_job SET claimed_until = NULL, due_at = now()
                WHERE recipe_id = :recipe_id
                """
            ),
            {"recipe_id": recipe_id},
        )

    def backlog(self) -> Backlog:
        row = self._session.execute(
            text("SELECT count(*) AS count, min(enqueued_at) AS oldest FROM embedding_job")
        ).one()
        return Backlog(count=row.count, oldest_enqueued_at=row.oldest)

    def failure_counts(self) -> dict[str, int]:
        rows = self._session.execute(
            text(
                """
                SELECT last_failure, count(*) AS count FROM embedding_job
                WHERE last_failure IS NOT NULL GROUP BY last_failure ORDER BY last_failure
                """
            )
        ).all()
        return {row.last_failure: row.count for row in rows}


class SqlAlchemyRecipeEmbeddings:
    def __init__(self, session: Session) -> None:
        self._session = session

    def content_for(self, recipe_ids: Sequence[UUID]) -> list[RecipeDetail]:
        recipes = SqlAlchemyRecipeRepository(self._session)
        details = (recipes.get_detail(recipe_id) for recipe_id in recipe_ids)
        return [detail for detail in details if detail is not None]

    def write_if_current(
        self,
        recipe_id: UUID,
        read_version: datetime,
        model: str,
        vector: Sequence[float],
        strategy: str,
        tokens: int | None,
        truncated: bool = False,
    ) -> bool:
        written = self._session.execute(
            text(
                """
                INSERT INTO recipe_embedding (
                    recipe_id, model, embedding, strategy_used, input_tokens, input_truncated,
                    recipe_updated_at, updated_at
                )
                SELECT r.id, :model, CAST(:vector AS vector), :strategy, :tokens, :truncated,
                       r.updated_at, clock_timestamp()
                FROM recipe r
                WHERE r.id = :recipe_id AND r.updated_at = :version
                ON CONFLICT (recipe_id, model) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    strategy_used = EXCLUDED.strategy_used,
                    input_tokens = EXCLUDED.input_tokens,
                    input_truncated = EXCLUDED.input_truncated,
                    recipe_updated_at = EXCLUDED.recipe_updated_at,
                    updated_at = EXCLUDED.updated_at
                RETURNING recipe_id
                """
            ),
            {
                "recipe_id": recipe_id,
                "version": read_version,
                "model": model,
                "vector": to_vector_text(vector),
                "strategy": strategy,
                "tokens": tokens,
                "truncated": truncated,
            },
        ).first()
        if written is None:
            return False
        self._session.execute(
            text(
                "DELETE FROM embedding_job WHERE recipe_id = :recipe_id "
                "AND claimed_until IS NOT NULL"
            ),
            {"recipe_id": recipe_id},
        )
        return True

    def search(
        self,
        notebook_ids: Sequence[UUID],
        filters: SearchFilters,
        model: str,
        query_vector: Sequence[float],
        limit: int,
    ) -> list[RawHit]:
        if not notebook_ids or limit < 1:
            return []
        rules = ["r.notebook_id = ANY(CAST(:notebook_ids AS uuid[]))"]
        params: dict[str, Any] = {
            "notebook_ids": list(notebook_ids),
            "model": model,
            "query": to_vector_text(query_vector),
            "limit": limit,
        }
        if filters.author_id is not None:
            rules.append("r.author_id = :author_id")
            params["author_id"] = filters.author_id
        if filters.created_after is not None:
            rules.append("r.created_at >= :created_after")
            params["created_after"] = filters.created_after
        if filters.created_before is not None:
            rules.append("r.created_at <= :created_before")
            params["created_before"] = filters.created_before
        if filters.exclude_recipe_ids:
            rules.append("NOT (r.id = ANY(CAST(:exclude AS uuid[])))")
            params["exclude"] = list(filters.exclude_recipe_ids)
        if filters.ingredient_names:
            # Every name must be on the recipe, compared as normalize_name does (FR-015a).
            rules.append(
                """
                (SELECT count(DISTINCT unaccent(lower(btrim(i.name))))
                 FROM recipe_ingredient i
                 WHERE i.recipe_id = r.id
                   AND unaccent(lower(btrim(i.name))) = ANY(CAST(:names AS text[]))) = :name_count
                """
            )
            params["names"] = list(filters.ingredient_names)
            params["name_count"] = len(filters.ingredient_names)
        rows = self._session.execute(
            text(
                f"""
                SELECT r.id, r.notebook_id, r.title,
                       1 - (e.embedding <=> CAST(:query AS vector)) AS score
                FROM recipe r
                JOIN recipe_embedding e
                  ON e.recipe_id = r.id
                 AND e.model = :model
                 AND e.recipe_updated_at = r.updated_at
                WHERE {" AND ".join(rules)}
                ORDER BY e.embedding <=> CAST(:query AS vector), r.id
                LIMIT :limit
                """
            ),
            params,
        ).all()
        return [
            RawHit(recipe_id=row.id, notebook_id=row.notebook_id, title=row.title, score=row.score)
            for row in rows
        ]
