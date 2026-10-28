"""Save a confirmed draft as a recipe (spec 020, contracts/save-api.md).

The use case does the checks and the writes. This module only maps each outcome to its
HTTP status and `code`. Errors are returned only for paths that stop before any insert
(research R4), so the request transaction stays empty.
"""

from __future__ import annotations

import uuid

from application.recipe_capture import TextTooLongError
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
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
    NotKitchenMemberError,
    RecipeChangedError,
    RecipeNotFoundError,
    RecipeReadOnlyError,
)
from domain.recipe_draft import (
    DraftProblems,
    IngredientLine,
    InvalidDraftError,
    clean_display_name,
)
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_delete_recipe,
    get_get_recipe,
    get_match_recipe_names,
    get_save_recipe_draft,
    get_update_recipe,
    require_user_alias,
)
from api.schemas.recipes import (
    NameMatch,
    NameMatchesBody,
    NameMatchesResponse,
    RecipeDetailResponse,
    RecipeLineResponse,
    RecipeNotebookResponse,
    RecipeSourceResponse,
    SaveRecipeBody,
    UpdateRecipeBody,
    UpdateRecipeResponse,
)

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
    except InvalidDraftError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_recipe", str(exc))
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
    )


def _not_found() -> JSONResponse:
    return _error(status.HTTP_404_NOT_FOUND, RecipeNotFoundError.CODE, RecipeNotFoundError.MESSAGE)


def _read_only() -> JSONResponse:
    return _error(status.HTTP_403_FORBIDDEN, RecipeReadOnlyError.CODE, RecipeReadOnlyError.MESSAGE)


@router.get("/recipes/{recipe_id}")
def get_recipe(
    recipe_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: GetRecipeService = Depends(get_get_recipe),
) -> JSONResponse:
    try:
        view = service.execute(GetRecipeCommand(actor_user_id=user_id, recipe_id=recipe_id))
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
    recipe_id: uuid.UUID,
    body: UpdateRecipeBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: UpdateRecipeService = Depends(get_update_recipe),
) -> JSONResponse:
    command = UpdateRecipeCommand(
        actor_user_id=user_id,
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
    )
    try:
        updated: UpdatedRecipe = service.execute(command)
    except RecipeNotFoundError:
        return _not_found()
    except RecipeReadOnlyError:
        return _read_only()
    except RecipeChangedError:
        return _error(status.HTTP_409_CONFLICT, RecipeChangedError.CODE, RecipeChangedError.MESSAGE)
    except DraftProblems as exc:
        return _problems(exc)
    except InvalidDraftError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_recipe", str(exc))
    response = UpdateRecipeResponse(
        **_detail(updated.view).model_dump(),
        created_catalog_names=list(updated.created_catalog_names),
    )
    return JSONResponse(content=response.model_dump(mode="json"))


@router.delete("/recipes/{recipe_id}")
def delete_recipe(
    recipe_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    service: DeleteRecipeService = Depends(get_delete_recipe),
) -> Response:
    try:
        service.execute(DeleteRecipeCommand(actor_user_id=user_id, recipe_id=recipe_id))
    except RecipeNotFoundError:
        return _not_found()
    except RecipeReadOnlyError:
        return _read_only()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
