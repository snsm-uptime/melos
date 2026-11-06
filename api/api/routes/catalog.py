"""Catalog management routes (spec 043 contracts/catalog.md).

The use cases do the checks and the writes; this module maps each outcome to its HTTP status and
`code`. A notebook the person cannot read is 404; read but not write is 403 on every change.
"""

from __future__ import annotations

import uuid

from application.catalog_manage import (
    DeleteNameService,
    DismissPairService,
    GetCatalogService,
    MergeCommand,
    MergePreviewCommand,
    MergePreviewService,
    MergeService,
    RenameCommand,
    RenameService,
    SplitService,
    SuggestPairsService,
)
from application.rate_limit import RateLimitPolicy, SlidingWindowRateLimiter
from domain.errors import (
    AIUnavailableError,
    CatalogNameBlankError,
    CatalogNameChangedError,
    CatalogNameExistsError,
    CatalogNameInUseError,
    CatalogNameOwnOtherError,
    CatalogNameUnknownError,
    CatalogReadOnlyError,
    DomainError,
    NotebookNotFoundError,
    SameIngredientError,
)
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_catalog_delete,
    get_catalog_dismiss_pair,
    get_catalog_merge,
    get_catalog_merge_preview,
    get_catalog_rename,
    get_catalog_split,
    get_catalog_suggest_pairs,
    get_get_catalog,
    get_rate_limiter,
    require_user_alias,
)
from api.schemas.catalog import (
    MergeBody,
    MergedNotebook,
    MergeNotebookResponse,
    MergePreviewBody,
    MergePreviewResponse,
    MergeResponse,
    PairBody,
    PairSuggestionsResponse,
    RenameBody,
    RenameResponse,
    SkippedNotebook,
    SplitBody,
    SplitResponse,
    catalog_response,
    ingredient_response,
)

router = APIRouter(tags=["catalog"])

# Each request is one model call per 300 names; the same order of cost as a capture.
PAIR_SUGGESTIONS_LIMIT = RateLimitPolicy(max_attempts=10, window_seconds=600)

_STATUS: dict[type[DomainError], int] = {
    NotebookNotFoundError: status.HTTP_404_NOT_FOUND,
    CatalogReadOnlyError: status.HTTP_403_FORBIDDEN,
    CatalogNameChangedError: status.HTTP_409_CONFLICT,
    CatalogNameExistsError: status.HTTP_409_CONFLICT,
    CatalogNameInUseError: status.HTTP_409_CONFLICT,
    CatalogNameOwnOtherError: status.HTTP_409_CONFLICT,
    CatalogNameBlankError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CatalogNameUnknownError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    SameIngredientError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    AIUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _error(exc: DomainError) -> JSONResponse:
    code = getattr(exc, "CODE", "error")
    if isinstance(exc, NotebookNotFoundError):
        code = NotebookNotFoundError.CODE
    detail: dict[str, object] = {"code": code}
    if isinstance(exc, CatalogNameExistsError):
        detail["existing"] = exc.existing
    if isinstance(exc, CatalogNameInUseError):
        detail["recipe_count"] = exc.recipe_count
    return JSONResponse(status_code=_STATUS[type(exc)], content={"detail": detail, **detail})


_HANDLED = tuple(_STATUS)


@router.get("/notebooks/{notebook_id}/catalog")
def get_catalog(
    notebook_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: GetCatalogService = Depends(get_get_catalog),
) -> JSONResponse:
    try:
        view = service.execute(user_id, notebook_id)
    except _HANDLED as exc:
        return _error(exc)
    return JSONResponse(content=catalog_response(view).model_dump(mode="json"))


@router.post("/notebooks/{notebook_id}/catalog/pair-suggestions")
def suggest_pairs(
    notebook_id: uuid.UUID,
    response: Response,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: SuggestPairsService = Depends(get_catalog_suggest_pairs),
    limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
) -> JSONResponse:
    allowed, retry_after = limiter.check_and_consume(
        f"catalog-pairs:{user_id}", PAIR_SUGGESTIONS_LIMIT
    )
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": {"code": "rate_limited"}, "code": "rate_limited"},
            headers={"Retry-After": str(retry_after)},
        )
    try:
        found = service.execute(user_id, notebook_id)
    except _HANDLED as exc:
        return _error(exc)
    body = PairSuggestionsResponse(pairs=[PairBody(en=en, es=es) for en, es in found.pairs])
    return JSONResponse(content=body.model_dump(mode="json"))


@router.post(
    "/notebooks/{notebook_id}/catalog/pair-dismissals", status_code=status.HTTP_204_NO_CONTENT
)
def dismiss_pair(
    notebook_id: uuid.UUID,
    body: PairBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: DismissPairService = Depends(get_catalog_dismiss_pair),
) -> Response:
    try:
        service.execute(user_id, notebook_id, body.en, body.es)
    except _HANDLED as exc:
        return _error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/notebooks/{notebook_id}/catalog/{name}")
def rename_name(
    notebook_id: uuid.UUID,
    name: str,
    body: RenameBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: RenameService = Depends(get_catalog_rename),
) -> JSONResponse:
    try:
        result = service.execute(
            RenameCommand(
                actor_user_id=user_id,
                notebook_id=notebook_id,
                name=name,
                new_name=body.new_name,
                language=body.language,
                set_language="language" in body.model_fields_set,
            )
        )
    except _HANDLED as exc:
        return _error(exc)
    item = ingredient_response(result.item)
    payload = RenameResponse(**item.model_dump(), recipes_changed=result.recipes_changed)
    return JSONResponse(content=payload.model_dump(mode="json"))


@router.delete("/notebooks/{notebook_id}/catalog/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_name(
    notebook_id: uuid.UUID,
    name: str,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: DeleteNameService = Depends(get_catalog_delete),
) -> Response:
    try:
        service.execute(user_id, notebook_id, name)
    except _HANDLED as exc:
        return _error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/notebooks/{notebook_id}/catalog/{name}/split")
def split_name(
    notebook_id: uuid.UUID,
    name: str,
    body: SplitBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: SplitService = Depends(get_catalog_split),
) -> JSONResponse:
    try:
        result = service.execute(user_id, notebook_id, name, body.other_name)
    except _HANDLED as exc:
        return _error(exc)
    payload = SplitResponse(
        kept=ingredient_response(result.kept),
        split=ingredient_response(result.split),
        recipes_changed=result.recipes_changed,
    )
    return JSONResponse(content=payload.model_dump(mode="json"))


@router.post("/catalog/merge-preview")
def merge_preview(
    body: MergePreviewBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: MergePreviewService = Depends(get_catalog_merge_preview),
) -> JSONResponse:
    try:
        preview = service.execute(
            MergePreviewCommand(user_id, body.from_notebook_id, body.merged, body.kept)
        )
    except _HANDLED as exc:
        return _error(exc)
    payload = MergePreviewResponse(
        merged=preview.merged,
        kept=preview.kept,
        merged_language=preview.merged_language,
        kept_language=preview.kept_language,
        notebooks=[
            MergeNotebookResponse(
                notebook_id=n.notebook_id, name=n.name, recipe_count=n.recipe_count
            )
            for n in preview.notebooks
        ],
    )
    return JSONResponse(content=payload.model_dump(mode="json"))


@router.post("/catalog/merge")
def merge(
    body: MergeBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: MergeService = Depends(get_catalog_merge),
) -> JSONResponse:
    result = service.execute(
        MergeCommand(
            actor_user_id=user_id,
            merged=body.merged,
            kept=body.kept,
            merged_language=body.merged_language,
            kept_language=body.kept_language,
            notebook_ids=tuple(body.notebook_ids),
        )
    )
    payload = MergeResponse(
        merged=[MergedNotebook(notebook_id=n, recipes_changed=c) for n, c in result.merged],
        skipped=[SkippedNotebook(notebook_id=n, reason=r) for n, r in result.skipped],
    )
    return JSONResponse(content=payload.model_dump(mode="json"))
