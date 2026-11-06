"""Save a confirmed draft as a recipe (spec 020, contracts/save-api.md).

The use case does the checks and the writes. This module only maps each outcome to its
HTTP status and `code`. Errors are returned only for paths that stop before any insert
(research R4), so the request transaction stays empty.
"""

from __future__ import annotations

import uuid

from application.ports import SessionRef
from application.recipe_capture import TextTooLongError
from application.recipe_locks import AcquireRecipeLockService, ReleaseRecipeLockService
from application.recipe_manage import (
    DeleteRecipeCommand,
    DeleteRecipeService,
    GetRecipeCommand,
    GetRecipeService,
    MatchRecipeNamesCommand,
    MatchRecipeNamesService,
    RecipeView,
    UpdatedRecipe,
    UpdateRecipeCommand,
    UpdateRecipeService,
)
from application.recipe_save import SavedRecipe, SaveRecipeCommand, SaveRecipeDraft
from application.recipe_share import (
    ListShareCandidatesService,
    ShareRecipeCommand,
    ShareRecipeService,
)
from domain.errors import (
    DomainError,
    InvalidPreviewImageError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
    NotEditingError,
    NotKitchenMemberError,
    RecipeChangedError,
    RecipeLockedError,
    RecipeNotFoundError,
    RecipeReadOnlyError,
    ShareRecipientNoDefaultNotebookError,
    ShareRecipientNotFoundError,
    ShareSelfError,
)
from domain.recipe_draft import (
    DraftProblems,
    IngredientLine,
    InvalidDraftError,
    clean_display_name,
)
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_acquire_recipe_lock,
    get_delete_recipe,
    get_get_recipe,
    get_list_share_candidates,
    get_match_recipe_names,
    get_release_recipe_lock,
    get_save_recipe_draft,
    get_share_recipe,
    get_update_recipe,
    require_session_ref,
    require_user_alias,
)
from api.schemas.carts import editor_response
from api.schemas.recipes import (
    NameMatch,
    NameMatchesBody,
    NameMatchesResponse,
    RecipeDetailResponse,
    RecipeLineResponse,
    RecipeLockResponse,
    RecipeNotebookResponse,
    RecipeSourceResponse,
    SaveRecipeBody,
    ShareCandidate,
    ShareCandidatesResponse,
    ShareRequest,
    ShareResponse,
    UpdateRecipeBody,
    UpdateRecipeResponse,
)
from api.worker import wake_embedding_worker

router = APIRouter(tags=["recipes"])


def _error(status_code: int, code: str, detail: str = "") -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


def _body(saved: SavedRecipe) -> dict:
    notebook = saved.notebook
    return {
        "recipe": {
            "id": str(saved.recipe.id),
            "title": saved.recipe.title,
            "notebook_id": str(saved.recipe.notebook_id),
        },
        "notebook": {
            "id": str(notebook.id),
            "kind": notebook.kind,
            "name": notebook.name,
            "kitchen_id": str(notebook.kitchen_id) if notebook.kitchen_id else None,
        },
        "created_catalog_names": list(saved.created_catalog_names),
    }


def _problems(problems: DraftProblems) -> JSONResponse:
    line_problems = [
        {"name": clean_display_name(problem.name), "kind": problem.kind.value}
        for problem in problems.line_problems
    ]
    if problems.missing:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": "",
                "code": "draft_incomplete",
                "missing": list(problems.missing),
                "line_problems": line_problems,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": "",
            "code": "ingredient_line_problem",
            "line_problems": line_problems,
        },
    )


@router.post("/recipes")
def save_recipe(
    request: Request,
    body: SaveRecipeBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    save: SaveRecipeDraft = Depends(get_save_recipe_draft),
) -> JSONResponse:
    command = SaveRecipeCommand(
        actor_user_id=user_id,
        save_key=body.save_key,
        notebook_id=body.notebook_id,
        kitchen_id=body.kitchen_id,
        source_text=body.source_text,
        title=body.title,
        base_servings=body.base_servings,
        servings_estimated=body.servings_estimated,
        lines=tuple(
            IngredientLine(
                name=line.name,
                vague=line.vague,
                quantity=line.quantity,
                unit=line.unit,
                size=line.size,
                note=line.note,
                preparation=line.preparation,
            )
            for line in body.ingredient_lines
        ),
        steps=tuple(body.steps),
        keep_units=tuple(body.keep_units),
        source_url=body.source_url,
        preview_image=body.preview_image,
    )
    try:
        saved = save.execute(command)
    except (NotebookNotFoundError, KitchenNotFoundError, NotKitchenMemberError):
        return _error(
            status.HTTP_404_NOT_FOUND, NotebookNotFoundError.CODE, NotebookNotFoundError.MESSAGE
        )
    except KitchenArchivedError:
        return _error(
            status.HTTP_409_CONFLICT, KitchenArchivedError.CODE, KitchenArchivedError.MESSAGE
        )
    except NotebookChoiceRequiredError:
        return _error(
            status.HTTP_409_CONFLICT,
            NotebookChoiceRequiredError.CODE,
            NotebookChoiceRequiredError.MESSAGE,
        )
    except TextTooLongError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, TextTooLongError.CODE, str(exc))
    except DraftProblems as exc:
        return _problems(exc)
    except InvalidPreviewImageError:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            InvalidPreviewImageError.CODE,
            InvalidPreviewImageError.MESSAGE,
        )
    except InvalidDraftError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_recipe", str(exc))
    if saved.created:
        wake_embedding_worker(request.app)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED if saved.created else status.HTTP_200_OK,
        content=_body(saved),
    )


def _detail(view: RecipeView) -> RecipeDetailResponse:
    detail, notebook = view.detail, view.notebook
    return RecipeDetailResponse(
        id=detail.id,
        title=detail.title,
        base_servings=detail.base_servings,
        servings_estimated=detail.servings_estimated,
        author_alias=detail.author_alias,
        created_at=detail.created_at,
        version=detail.updated_at,
        notebook=RecipeNotebookResponse(
            id=notebook.id,
            name=notebook.name,
            kind=notebook.kind,
            kitchen_id=notebook.kitchen_id,
        ),
        can_write=view.can_write,
        ingredient_lines=[
            RecipeLineResponse(
                name=line.name,
                vague=line.vague,
                quantity=line.quantity,
                unit=line.unit,
                size=line.size,
                preparation=line.preparation,
                note=line.note,
            )
            for line in detail.lines
        ],
        steps=list(detail.steps),
        source=(
            RecipeSourceResponse(type=detail.source_type or "url", url=detail.source_url)
            if detail.source_url
            else None
        ),
        preview_image=detail.preview_image,
        editor=editor_response(view.editor),
        in_cart=view.cart.in_cart if view.cart is not None else None,
        cart_editor=editor_response(view.cart.editor) if view.cart is not None else None,
    )


def _not_found() -> JSONResponse:
    return _error(status.HTTP_404_NOT_FOUND, RecipeNotFoundError.CODE, RecipeNotFoundError.MESSAGE)


def _read_only() -> JSONResponse:
    return _error(status.HTTP_403_FORBIDDEN, RecipeReadOnlyError.CODE, RecipeReadOnlyError.MESSAGE)


def _locked(exc: RecipeLockedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),
            "code": RecipeLockedError.CODE,
            "editor_alias": exc.editor_alias,
        },
    )


def _not_editing() -> JSONResponse:
    return _error(status.HTTP_409_CONFLICT, NotEditingError.CODE, NotEditingError.MESSAGE)


@router.get("/recipes/share-candidates", response_model=ShareCandidatesResponse)
def list_share_candidates(
    user_id: uuid.UUID = Depends(require_user_alias),
    service: ListShareCandidatesService = Depends(get_list_share_candidates),
) -> ShareCandidatesResponse:
    """The people the caller may share a recipe with: co-members only (spec 071 FR-002)."""
    candidates = service.execute(user_id)
    return ShareCandidatesResponse(
        candidates=[
            ShareCandidate(user_id=candidate.user_id, alias=candidate.alias)
            for candidate in candidates
        ]
    )


@router.post(
    "/recipes/{recipe_id}/share",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
)
def share_recipe(
    request: Request,
    recipe_id: uuid.UUID,
    body: ShareRequest,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: ShareRecipeService = Depends(get_share_recipe),
) -> ShareResponse | JSONResponse:
    """Copy a readable recipe into a co-member's default notebook (spec 071 FR-008, FR-011)."""
    try:
        shared = service.execute(
            ShareRecipeCommand(
                actor_id=user_id,
                recipe_id=recipe_id,
                recipient_id=body.recipient_user_id,
            )
        )
    except RecipeNotFoundError as exc:
        return _share_error(status.HTTP_404_NOT_FOUND, exc)
    except ShareRecipientNotFoundError as exc:
        return _share_error(status.HTTP_404_NOT_FOUND, exc)
    except ShareSelfError as exc:
        return _share_error(status.HTTP_409_CONFLICT, exc)
    except ShareRecipientNoDefaultNotebookError as exc:
        return _share_error(status.HTTP_422_UNPROCESSABLE_CONTENT, exc)
    wake_embedding_worker(request.app)
    return ShareResponse(
        recipe_id=shared.recipe_id,
        recipient_alias=shared.recipient_alias,
        notebook_id=shared.notebook_id,
    )


def _share_error(status_code: int, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.MESSAGE, "code": exc.CODE},
    )


@router.get("/recipes/{recipe_id}")
def get_recipe(
    recipe_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: GetRecipeService = Depends(get_get_recipe),
) -> JSONResponse:
    try:
        view = service.execute(
            GetRecipeCommand(actor_user_id=ref.user_id, recipe_id=recipe_id, session=ref)
        )
    except RecipeNotFoundError:
        return _not_found()
    return JSONResponse(content=_detail(view).model_dump(mode="json"))


@router.post("/recipes/{recipe_id}/name-matches")
def match_recipe_names(
    recipe_id: uuid.UUID,
    body: NameMatchesBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: MatchRecipeNamesService = Depends(get_match_recipe_names),
) -> JSONResponse:
    if any(not name.strip() for name in body.names):
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_recipe", "name")
    try:
        matches = service.execute(
            MatchRecipeNamesCommand(
                actor_user_id=user_id, recipe_id=recipe_id, names=tuple(body.names)
            )
        )
    except RecipeNotFoundError:
        return _not_found()
    except RecipeReadOnlyError:
        return _read_only()
    response = NameMatchesResponse(
        matches=[NameMatch(name=name, entry=entry) for name, entry in matches]
    )
    return JSONResponse(content=response.model_dump(mode="json"))


@router.put("/recipes/{recipe_id}")
def update_recipe(
    request: Request,
    recipe_id: uuid.UUID,
    body: UpdateRecipeBody,
    ref: SessionRef = Depends(require_session_ref),
    service: UpdateRecipeService = Depends(get_update_recipe),
) -> JSONResponse:
    command = UpdateRecipeCommand(
        actor_user_id=ref.user_id,
        session_id=ref.session_id,
        recipe_id=recipe_id,
        version=body.version,
        title=body.title,
        base_servings=body.base_servings,
        servings_estimated=body.servings_estimated,
        lines=tuple(
            IngredientLine(
                name=line.name,
                vague=line.vague,
                quantity=line.quantity,
                unit=line.unit,
                size=line.size,
                note=line.note,
                preparation=line.preparation,
            )
            for line in body.ingredient_lines
        ),
        steps=tuple(body.steps),
        keep_units=tuple(body.keep_units),
        change_image="preview_image" in body.model_fields_set,
        preview_image=body.preview_image,
    )
    try:
        updated: UpdatedRecipe = service.execute(command)
    except RecipeNotFoundError:
        return _not_found()
    except RecipeReadOnlyError:
        return _read_only()
    except RecipeLockedError as exc:
        return _locked(exc)
    except NotEditingError:
        return _not_editing()
    except RecipeChangedError:
        return _error(status.HTTP_409_CONFLICT, RecipeChangedError.CODE, RecipeChangedError.MESSAGE)
    except DraftProblems as exc:
        return _problems(exc)
    except InvalidPreviewImageError:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            InvalidPreviewImageError.CODE,
            InvalidPreviewImageError.MESSAGE,
        )
    except InvalidDraftError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_recipe", str(exc))
    wake_embedding_worker(request.app)
    response = UpdateRecipeResponse(
        **_detail(updated.view).model_dump(),
        created_catalog_names=list(updated.created_catalog_names),
    )
    return JSONResponse(content=response.model_dump(mode="json"))


@router.delete("/recipes/{recipe_id}")
def delete_recipe(
    recipe_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: DeleteRecipeService = Depends(get_delete_recipe),
) -> Response:
    try:
        service.execute(
            DeleteRecipeCommand(
                actor_user_id=ref.user_id, recipe_id=recipe_id, session_id=ref.session_id
            )
        )
    except RecipeNotFoundError:
        return _not_found()
    except RecipeReadOnlyError:
        return _read_only()
    except RecipeLockedError as exc:
        return _locked(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/recipes/{recipe_id}/edit-lock")
def acquire_recipe_lock(
    recipe_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: AcquireRecipeLockService = Depends(get_acquire_recipe_lock),
) -> JSONResponse:
    """Take the recipe lock, or keep it alive for its holder (spec 022, recipe-lock-api.md)."""
    try:
        editor = service.execute(ref, recipe_id)
    except RecipeNotFoundError:
        return _not_found()
    except RecipeReadOnlyError:
        return _read_only()
    except RecipeLockedError as exc:
        return _locked(exc)
    body = RecipeLockResponse(editor=editor_response(editor))  # type: ignore[arg-type]
    return JSONResponse(content=body.model_dump(mode="json"))


@router.delete("/recipes/{recipe_id}/edit-lock")
def release_recipe_lock(
    recipe_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: ReleaseRecipeLockService = Depends(get_release_recipe_lock),
) -> Response:
    service.execute(ref, recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
