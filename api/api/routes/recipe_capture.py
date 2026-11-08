"""Recipe capture from pasted text (spec 016) and from a link (spec 026), and the units lists.

The use case does the checks and the assistant call. This module only maps each
outcome to its HTTP status and `code` (contracts/capture-api.md). Messages carry no
service text, keys or traces (FR-029).
"""

from __future__ import annotations

import base64
import uuid
from typing import Any

from application.ports import PageFetchFailed, PreferencesRepository, UnitRepository
from application.recipe_capture import (
    CapturedDraft,
    CaptureOutcome,
    CaptureRecipeCommand,
    CaptureRecipeText,
    TextEmptyError,
    TextTooLongError,
)
from application.recipe_capture_picture import (
    CapturedPictureDraft,
    CapturePictureCommand,
    CapturePictureRecipe,
)
from application.recipe_capture_url import (
    CapturedPageDraft,
    CaptureRecipeUrl,
    CaptureRecipeUrlCommand,
    PageNoRecipe,
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
from application.recipe_vocabulary import check_unit_word, vocabulary_for_person
from application.units import available_units
from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.ingredient_catalog import LineMatch, as_language
from domain.page_link import MAX_LINK_CHARS, PageLinkRefused
from domain.preferences import effective_language
from domain.recipe_draft import clean_display_name
from domain.recipe_picture import PictureRefused
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_capture_recipe_picture,
    get_capture_recipe_text,
    get_capture_recipe_url,
    get_preferences_repository,
    get_unit_repository,
    get_vocabulary_answer,
    require_user_alias,
)
from api.schemas.recipe_capture import (
    CapturePictureBody,
    CaptureTextBody,
    CaptureUrlBody,
    UnitCheckBody,
)
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


def _match_body(match: LineMatch | None, shown: str) -> dict[str, Any]:
    if match is None or match.kind == "new":
        return {"kind": "new", "entry": None}
    # The name the line shows in the draft's language (spec 043), which is the line's name.
    return {"kind": "matched", "entry": shown}


def _draft_language(
    captured: CapturedDraft | CapturedPageDraft | CapturedPictureDraft,
) -> str:
    """The draft's language: the detected one, else the interface's, else Spanish (FR-005a)."""
    return captured.recipe.language or as_language(captured.language) or "es"


def _draft_body(
    captured: CapturedDraft | CapturedPageDraft | CapturedPictureDraft,
) -> dict[str, Any]:
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
            "language": _draft_language(captured),
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
                    "vague_text": line.vague_text,
                    "note": line.note,
                    "text_name": line.text_name,
                    "match": _match_body(matches[index], line.name),
                }
                for index, line in enumerate(recipe.ingredient_lines)
            ],
            "unknown_units": [
                {"word": unknown.word, "lines": list(unknown.lines)}
                for unknown in recipe.unknown_units
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


def _language(request: Request, prefs: PreferencesRepository, user_id: uuid.UUID) -> str:
    record = prefs.get_preferences(user_id)
    return effective_language(
        record.language if record else None,
        request.headers.get("accept-language"),
    )


# One body for every fetch failure, blocked addresses included, so the message never lets a
# member probe the network (spec 026 R10, FR-024): no kind, address or site text. The one
# exception is a refusal the public site itself answered (401/402/403/451), which reveals nothing
# about the network and gets its own code (spec 067 R2), still without status, domain or text.
def _page_fetch_failed() -> JSONResponse:
    return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "page_fetch_failed", "")


def _site_requires_license() -> JSONResponse:
    return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "site_requires_license", "")


def _link_refused(exc: PageLinkRefused) -> JSONResponse:
    if exc.kind in ("credentials", "port"):
        return _page_fetch_failed()
    if exc.kind == "empty":
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "link_empty", "")
    if exc.kind == "too_long":
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": "", "code": "link_too_long", "max": MAX_LINK_CHARS},
        )
    return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "link_invalid", "")


@router.post("/notebooks/{notebook_id}/captures/url")
def capture_recipe_url(
    notebook_id: uuid.UUID,
    body: CaptureUrlBody,
    request: Request,
    user_id: uuid.UUID = Depends(require_user_alias),
    capture: CaptureRecipeUrl = Depends(get_capture_recipe_url),
    prefs: PreferencesRepository = Depends(get_preferences_repository),
) -> JSONResponse:
    """A draft from the one page the link points to (spec 026, contracts/capture-url-api.md)."""
    try:
        outcome = capture.execute(
            CaptureRecipeUrlCommand(
                actor_user_id=user_id,
                notebook_id=notebook_id,
                url=body.url,
                language=_language(request, prefs, user_id),
            )
        )
    except PageLinkRefused as exc:
        return _link_refused(exc)
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
    if isinstance(outcome, PageFetchFailed):
        if outcome.kind == "refused":
            return _site_requires_license()
        return _page_fetch_failed()
    if isinstance(outcome, PageNoRecipe):
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "page_no_recipe", "")
    if isinstance(outcome, CapturedPageDraft):
        content = _draft_body(outcome)
        content["page"] = {
            "source_url": outcome.source_url,
            "preview_image": outcome.preview_image,
            "cut": outcome.page_cut,
        }
        return JSONResponse(status_code=status.HTTP_200_OK, content=content)
    if isinstance(outcome, NotARecipe) and outcome.reason != NotRecipeReason.MULTIPLE_RECIPES:
        # The use case never returns this; a page that is not a recipe is page_no_recipe.
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "page_no_recipe", "")
    return _outcome_response(outcome)


def _picture_refused(exc: PictureRefused) -> JSONResponse:
    """The picture itself cannot be used. Codes only, never the file name or technical text."""
    code = {
        "empty": "picture_empty",
        "unsupported": "picture_unsupported",
        "too_large": "picture_too_large",
    }[exc.kind]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "", "code": code},
    )


def _picture_body(outcome: CapturedPictureDraft) -> dict[str, Any]:
    """The draft, with the compressed picture's metadata in place of the link's `page` key."""
    content = _draft_body(outcome)
    picture = outcome.picture
    content["picture"] = {
        "tier": picture.tier.value,
        "sharpness": picture.sharpness,
        "original_dimensions": list(picture.original_dimensions),
        "final_dimensions": list(picture.final_dimensions),
        "size_kb": picture.size_kb,
        "steps_taken": [
            {"quality": step.quality, "max_side": step.max_side} for step in picture.steps_taken
        ],
        # The processed WebP only: the original upload is never kept or sent back.
        "preview_image": "data:image/webp;base64," + base64.b64encode(picture.webp).decode("ascii"),
    }
    return content


@router.post("/notebooks/{notebook_id}/captures/picture")
def capture_recipe_picture(
    notebook_id: uuid.UUID,
    body: CapturePictureBody,
    request: Request,
    user_id: uuid.UUID = Depends(require_user_alias),
    capture: CapturePictureRecipe = Depends(get_capture_recipe_picture),
    prefs: PreferencesRepository = Depends(get_preferences_repository),
) -> JSONResponse:
    """A draft from one cookbook photo (spec 041, contracts/capture-picture-api.md)."""
    try:
        outcome = capture.execute(
            CapturePictureCommand(
                actor_user_id=user_id,
                notebook_id=notebook_id,
                image_base64=body.image_base64,
                handwritten=body.handwritten,
                language=_language(request, prefs, user_id),
            )
        )
    except PictureRefused as exc:
        return _picture_refused(exc)
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
    if isinstance(outcome, CapturedPictureDraft):
        return JSONResponse(status_code=status.HTTP_200_OK, content=_picture_body(outcome))
    return _outcome_response(outcome)


@router.get("/recipe-vocabulary")
def recipe_vocabulary(
    request: Request,
    user_id: uuid.UUID = Depends(require_user_alias),
    units: UnitRepository = Depends(get_unit_repository),
) -> dict[str, Any]:
    available = available_units(units.extras_for(user_id))
    return vocabulary_for_person(get_vocabulary_answer(request), available)


@router.post("/recipe-vocabulary/unit-check")
def recipe_unit_check(
    body: UnitCheckBody,
    user_id: uuid.UUID = Depends(require_user_alias),
    units: UnitRepository = Depends(get_unit_repository),
) -> dict[str, str | None]:
    """Whether a typed word is a unit the caller has. Stores nothing (spec 055 R12)."""
    answer = check_unit_word(body.word, available_units(units.extras_for(user_id)))
    return {"outcome": answer.outcome, "unit": answer.unit}
