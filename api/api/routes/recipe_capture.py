"""Recipe capture from pasted text, and the controlled vocabulary (spec 016).

The use case does the checks and the assistant call. This module only maps each
outcome to its HTTP status and `code` (contracts/capture-api.md). Messages carry no
service text, keys or traces (FR-029).
"""

from __future__ import annotations

import uuid
from typing import Any

from application.ports import PreferencesRepository
from application.recipe_capture import (
    CapturedDraft,
    CaptureOutcome,
    CaptureRecipeCommand,
    CaptureRecipeText,
    TextEmptyError,
    TextTooLongError,
)
from application.recipe_extraction import (
    ONE_RECIPE_REASON,
    AIProviderError,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    Unavailable,
)
from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.labels import pick_label
from domain.preferences import effective_language
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_capture_recipe_text,
    get_preferences_repository,
    get_vocabulary_answer,
    require_user_alias,
)
from api.schemas.recipe_capture import CaptureTextBody
from api.settings import load_recipe_text_max_chars

router = APIRouter(tags=["recipe-capture"])

MAX_REASON_CHARS = 120


def _error(
    status_code: int, code: str, detail: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
        headers=headers,
    )


def _draft_body(captured: CapturedDraft, vocabulary: dict[str, Any]) -> dict[str, Any]:
    language = captured.language
    main_labels = {item["id"]: item["label"] for item in vocabulary["main_ingredients"]}
    cuisines = {item["id"]: item for item in vocabulary["cuisines"]}
    recipe = captured.recipe
    notebook = captured.notebook
    return {
        "outcome": "draft",
        "notebook": {
            "id": str(notebook.id),
            "kind": notebook.kind,
            "name": notebook.name,
            "kitchen_id": str(notebook.kitchen_id) if notebook.kitchen_id else None,
        },
        "language": language,
        "draft": {
            "title": recipe.title,
            "base_servings": recipe.base_servings,
            "servings_estimated": recipe.servings_estimated,
            "main_ingredients": [
                {"id": key, "label": pick_label(main_labels[key], language)}
                for key in recipe.main_ingredients
            ],
            "cuisines": [
                {
                    "id": key,
                    "label": pick_label(cuisines[key]["label"], language),
                    "tag": cuisines[key]["tag"],
                }
                for key in recipe.cuisines
            ],
            "ingredient_lines": [
                {
                    "name": line.name,
                    "vague": line.vague,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "size": line.size,
                    "preparation": line.preparation,
                    "note": line.note,
                }
                for line in recipe.ingredient_lines
            ],
            "steps": list(recipe.steps),
        },
    }


def _outcome_response(outcome: CaptureOutcome, vocabulary: dict[str, Any]) -> JSONResponse:
    if isinstance(outcome, CapturedDraft):
        return JSONResponse(
            status_code=status.HTTP_200_OK, content=_draft_body(outcome, vocabulary)
        )
    if isinstance(outcome, NotARecipe):
        if outcome.reason == ONE_RECIPE_REASON:
            return _error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "one_recipe_at_a_time",
                "Upload only one recipe at a time.",
            )
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "not_a_recipe",
            outcome.reason[:MAX_REASON_CHARS],
        )
    if isinstance(outcome, InvalidOutput):
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ai_invalid_output",
            "The assistant's answer could not be read as a recipe.",
        )
    if isinstance(outcome, LimitReached):
        headers = None
        if outcome.retry_after_seconds is not None:
            headers = {"Retry-After": str(outcome.retry_after_seconds)}
        return _error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "ai_limit_reached",
            "The assistant's usage limit was reached.",
            headers,
        )
    if isinstance(outcome, Unavailable):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_unavailable",
            "The assistant did not answer in time.",
        )
    if isinstance(outcome, AIProviderError):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_misconfigured",
            "The assistant is not set up for this deployment.",
        )
    raise AssertionError(f"unexpected capture outcome {outcome!r}")


@router.post("/notebooks/{notebook_id}/captures/text")
def capture_recipe_text(
    notebook_id: uuid.UUID,
    body: CaptureTextBody,
    request: Request,
    user_id: uuid.UUID = Depends(require_user_alias),
    capture: CaptureRecipeText = Depends(get_capture_recipe_text),
    prefs: PreferencesRepository = Depends(get_preferences_repository),
) -> JSONResponse:
    max_chars = load_recipe_text_max_chars()
    # Guard at twice the limit, so grossly oversized bodies fail before any work (FR-002).
    if len(body.text) > 2 * max_chars:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "text_too_long",
            f"That text is too long. Paste up to {max_chars} characters.",
        )
    record = prefs.get_preferences(user_id)
    language = effective_language(
        record.language if record else None,
        request.headers.get("accept-language"),
    )
    try:
        outcome = capture.execute(
            CaptureRecipeCommand(
                actor_user_id=user_id,
                notebook_id=notebook_id,
                text=body.text,
                language=language,
            )
        )
    except TextEmptyError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, TextEmptyError.CODE, str(exc))
    except TextTooLongError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, TextTooLongError.CODE, str(exc))
    except NotebookNotFoundError:
        return _error(
            status.HTTP_404_NOT_FOUND, NotebookNotFoundError.CODE, NotebookNotFoundError.MESSAGE
        )
    except KitchenArchivedError:
        return _error(
            status.HTTP_409_CONFLICT, KitchenArchivedError.CODE, KitchenArchivedError.MESSAGE
        )
    return _outcome_response(outcome, get_vocabulary_answer(request))


@router.get("/recipe-vocabulary")
def recipe_vocabulary(
    request: Request,
    user_id: uuid.UUID = Depends(require_user_alias),
) -> dict[str, Any]:
    return get_vocabulary_answer(request)
