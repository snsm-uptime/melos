"""Save a confirmed draft as a recipe (spec 020, contracts/save-api.md).

The use case does the checks and the writes. This module only maps each outcome to its
HTTP status and `code`. Errors are returned only for paths that stop before any insert
(research R4), so the request transaction stays empty.
"""

from __future__ import annotations

import uuid

from application.recipe_capture import TextTooLongError
from application.recipe_save import SavedRecipe, SaveRecipeCommand, SaveRecipeDraft
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
    NotKitchenMemberError,
)
from domain.recipe_draft import (
    DraftProblems,
    IngredientLine,
    InvalidDraftError,
    clean_display_name,
)
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.deps import get_save_recipe_draft, require_user_alias
from api.schemas.recipes import SaveRecipeBody

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
