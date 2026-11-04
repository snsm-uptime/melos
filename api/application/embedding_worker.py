"""Background jobs of the api: embedding pending recipes and cleaning up search records (spec 019).

One pass of `EmbedPendingRecipes`:

1. claim due jobs (`SKIP LOCKED`, with a lease) and commit;
2. read each recipe's content and version, and commit, so no transaction stays open during the
   service call;
3. embed the texts in one call (one attempt), and count tokens when the service did not say;
4. write each embedding only if the recipe is unchanged; a changed one is due again at once;
5. on failure, each job waits by the shared retry rule (domain.retry), with no limit on tries.

Logs carry counts and result class names only (FR-023).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.embed_text import STRATEGIES
from domain.retry import DEFAULT_POLICY, RetryPolicy, next_wait

from application.ports import (
    Embedded,
    Embedder,
    EmbeddingJobs,
    EmbedTextStrategy,
    RecipeDetail,
    RecipeEmbeddings,
    SearchRecords,
    TransactionCommitter,
)

logger = logging.getLogger(__name__)

# A claim lasts this long; a process that dies mid-call frees its jobs after it (research R4).
LEASE_S = 120.0


@dataclass(frozen=True, slots=True)
class NamedStrategy:
    name: str
    _render: Callable[[RecipeDetail], str]

    def render(self, recipe: RecipeDetail) -> str:
        return self._render(recipe)


def strategy_named(name: str) -> EmbedTextStrategy:
    """The configured text strategy; KeyError for an unknown name."""
    return NamedStrategy(name, STRATEGIES[name])


class EmbedPendingRecipes:
    def __init__(
        self,
        jobs: EmbeddingJobs,
        embeddings: RecipeEmbeddings,
        embedder: Embedder,
        strategy: EmbedTextStrategy,
        committer: TransactionCommitter,
        *,
        batch_size: int = 1,
        timeout_s: float = 10.0,
        policy: RetryPolicy = DEFAULT_POLICY,
        lease_s: float = LEASE_S,
    ) -> None:
        self._jobs = jobs
        self._embeddings = embeddings
        self._embedder = embedder
        self._strategy = strategy
        self._committer = committer
        self._batch_size = batch_size
        self._timeout_s = timeout_s
        self._policy = policy
        self._lease_s = lease_s

    def run_once(self) -> int:
        """Handle one batch of due jobs; returns how many were claimed (0: nothing was due)."""
        if not self._embedder.configured:
            return 0
        claimed = self._jobs.claim(self._batch_size, self._lease_s)
        self._committer.commit()
        if not claimed:
            return 0
        details = self._embeddings.content_for([job.recipe_id for job in claimed])
        self._committer.commit()
        if not details:
            # Deleted meanwhile: their jobs went with them.
            return len(claimed)

        texts = [self._strategy.render(detail) for detail in details]
        result = self._embedder.embed_documents(
            texts, [detail.title for detail in details], self._timeout_s
        )
        if isinstance(result, Embedded):
            tokens = [
                count if count is not None else self._embedder.count_tokens(text, self._timeout_s)
                for text, count in zip(texts, result.token_counts, strict=True)
            ]
            written = changed = 0
            for detail, vector, count, truncated in zip(
                details, result.vectors, tokens, result.truncated, strict=True
            ):
                if self._embeddings.write_if_current(
                    detail.id,
                    detail.updated_at,
                    self._embedder.model,
                    vector,
                    self._strategy.name,
                    count,
                    truncated,
                ):
                    written += 1
                else:
                    self._jobs.release_changed(detail.id)
                    changed += 1
            self._committer.commit()
            logger.info("embedding pass outcome=embedded written=%d changed=%d", written, changed)
            return len(claimed)

        failure = type(result).__name__
        service_wait = getattr(result, "retry_after_seconds", None)
        waits = {job.recipe_id: job.last_wait_s for job in claimed}
        for detail in details:
            wait = next_wait(waits.get(detail.id), self._policy, service_wait)
            self._jobs.fail(detail.id, wait, failure)
        self._committer.commit()
        logger.warning("embedding pass outcome=failed class=%s jobs=%d", failure, len(details))
        return len(claimed)


class CleanUpSearchRecords:
    """Delete search records older than the retention (spec 019 FR-017e)."""

    def __init__(
        self, records: SearchRecords, committer: TransactionCommitter, *, retention_days: int
    ) -> None:
        self._records = records
        self._committer = committer
        self._retention = timedelta(days=retention_days)

    def run(self, now: datetime) -> int:
        deleted = self._records.delete_older_than(now - self._retention)
        self._committer.commit()
        logger.info("search record clean-up deleted=%d", deleted)
        return deleted
