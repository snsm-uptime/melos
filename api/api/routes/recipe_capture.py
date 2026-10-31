"""Recipe capture from pasted text, and the units and sizes lists (spec 016).

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
    AIProviderError,
    DraftIncomplete,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    NotRecipeReason,
    Unavailable,
)
from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.ingredient_catalog import LineMatch
from domain.preferences import effective_language
from domain.recipe_draft import clean_display_name
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

# MVP-OUT: the draft no longer uses `domain.labels.pick_label` (category chip labels)
router = APIRouter(tags=["recipe-capture"])


def _error(
    status_code: int, code: str, detail: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
        headers=headers,
    )


def _match_body(match: LineMatch | None) -> dict[str, Any]:
    if match is None or match.kind == "new":
        return {"kind": "new", "entry": None}
    return {"kind": "matched", "entry": match.entry}


def _draft_body(captured: CapturedDraft) -> dict[str, Any]:
    language = captured.language
    # MVP-OUT: main_labels = {item["id"]: item["label"] for item in vocabulary["main_ingredients"]}
    # MVP-OUT: cuisines = {item["id"]: item for item in vocabulary["cuisines"]}
    recipe = captured.recipe
    notebook = captured.notebook
    # A draft from the service always has one match per line; a draft without them shows "new".
    matches: list[LineMatch | None] = [
        recipe.matches[index] if index < len(recipe.matches) else None
        for index in range(len(recipe.ingredient_lines))
    ]
    return {
        "outcome": "draft",
        "notebook": {
            "id": str(notebook.id),
            "kind": notebook.kind,
            "name": notebook.name,
            "kitchen_id": str(notebook.kitchen_id) if notebook.kitchen_id else None,
        },
        "language": language,
        "catalog": sorted(captured.catalog),
        "draft": {
            "changes": [
                {"line": change.line, "from": change.from_name, "to": change.to}
                for change in recipe.changes
            ],
            "title": recipe.title,
            "base_servings": recipe.base_servings,
            "servings_estimated": recipe.servings_estimated,
            # MVP-OUT: "main_ingredients": [
            # MVP-OUT:     {"id": key, "label": pick_label(main_labels[key], language)}
            # MVP-OUT:     for key in recipe.main_ingredients
            # MVP-OUT: ],
            # MVP-OUT: "cuisines": [
            # MVP-OUT:     {
            # MVP-OUT:         "id": key,
            # MVP-OUT:         "label": pick_label(cuisines[key]["label"], language),
            # MVP-OUT:         "tag": cuisines[key]["tag"],
            # MVP-OUT:     }
            # MVP-OUT:     for key in recipe.cuisines
            # MVP-OUT: ],
            "ingredient_lines": [
                {
                    "name": line.name,
                    "vague": line.vague,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "size": line.size,
                    "preparation": line.preparation,
                    "note": line.note,
                    "text_name": line.text_name,
                    "match": _match_body(matches[index]),
                }
                for index, line in enumerate(recipe.ingredient_lines)
            ],
            "steps": list(recipe.steps),
        },
    }


def _outcome_response(outcome: CaptureOutcome) -> JSONResponse:
    if isinstance(outcome, CapturedDraft):
        return JSONResponse(status_code=status.HTTP_200_OK, content=_draft_body(outcome))
    if isinstance(outcome, NotARecipe):
        if outcome.reason == NotRecipeReason.MULTIPLE_RECIPES:
            return _error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "one_recipe_at_a_time",
                "",
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": outcome.reason.value,
                "code": "not_a_recipe",
                "ingredient": outcome.ingredient,
            },
        )
    if isinstance(outcome, DraftIncomplete):
        problems = outcome.problems
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
    if isinstance(outcome, InvalidOutput):
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ai_invalid_output",
            "",
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
        capture_command = CaptureRecipeCommand(
            actor_user_id=user_id,
            notebook_id=notebook_id,
            text=body.text,
            language=language,
        )
        outcome = capture.execute(capture_command)
    except TextEmptyError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, TextEmptyError.CODE, str(exc))
    except TextTooLongError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, TextTooLongError.CODE, str(exc))
    except NotebookNotFoundError:
        return _error(
            status.HTTP_404_NOT_FOUND,
            NotebookNotFoundError.CODE,
            NotebookNotFoundError.MESSAGE,
        )
    except KitchenArchivedError:
        return _error(
            status.HTTP_409_CONFLICT,
            KitchenArchivedError.CODE,
            KitchenArchivedError.MESSAGE,
        )
    return _outcome_response(outcome)


@router.get("/recipe-vocabulary")
def recipe_vocabulary(
    request: Request,
    user_id: uuid.UUID = Depends(require_user_alias),
) -> dict[str, Any]:
    return get_vocabulary_answer(request)
