"""Search result records in Postgres (spec 019 FR-017b to FR-017e).

A record holds the asking feature, the scope kind, the model, the strategy and each result's
rank, score and mark. It never holds a person, a question, a kitchen or a notebook id.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from application.ports import Band, RecordedHit, SearchEventRecord
from sqlalchemy import delete, insert, text
from sqlalchemy.orm import Session

from adapters.persistence.models import SearchEventModel, SearchResultModel


class SqlAlchemySearchRecords:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, event: SearchEventRecord, hits: Sequence[RecordedHit]) -> UUID:
        search_id = self._session.execute(
            insert(SearchEventModel)
            .values(
                feature=event.feature,
                scope_kind=event.scope_kind,
                result_count=len(hits),
                model=event.model,
                strategy=event.strategy,
                min_closeness=event.min_closeness,
            )
            .returning(SearchEventModel.id)
        ).scalar_one()
        if hits:
            self._session.execute(
                insert(SearchResultModel),
                [
                    {
                        "search_id": search_id,
                        "recipe_id": hit.recipe_id,
                        "rank": hit.rank,
                        "score": hit.score,
                        "mark": hit.mark,
                    }
                    for hit in hits
                ],
            )
        return search_id

    def mark_used(self, search_id: UUID, recipe_id: UUID) -> bool:
        found = self._session.execute(
            text(
                """
                UPDATE search_result SET used_at = coalesce(used_at, now())
                WHERE search_id = :search_id AND recipe_id = :recipe_id
                RETURNING 1
                """
            ),
            {"search_id": search_id, "recipe_id": recipe_id},
        ).first()
        return found is not None

    def delete_older_than(self, cutoff: datetime) -> int:
        result = self._session.execute(
            delete(SearchEventModel).where(SearchEventModel.created_at < cutoff)
        )
        return result.rowcount or 0

    def score_bands(self, width: float) -> list[Band]:
        if not math.isfinite(width) or width <= 0:
            raise ValueError("band width must be > 0")
        rows = self._session.execute(
            text(
                """
                SELECT floor(score / :width) AS band,
                       count(*) AS shown,
                       count(used_at) AS used
                FROM search_result
                GROUP BY band
                ORDER BY band
                """
            ),
            {"width": width},
        ).all()
        return [
            Band(
                low=round(row.band * width, 6),
                high=round((row.band + 1) * width, 6),
                shown=row.shown,
                used=row.used,
            )
            for row in rows
        ]
