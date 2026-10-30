"""The kitchen cart (spec 022, contracts/cart-api.md).

The use cases do the checks and the writes; this module maps each outcome to its HTTP
status and `code`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from application.carts import (
    AddToDraftService,
    CartView,
    DiscardCartService,
    GetCartService,
    RemoveFromDraftService,
    ReplaceDraftService,
    SaveCartService,
    StartCartEditService,
)
from application.ports import SessionRef
from domain.errors import (
    CartLockedError,
    CartValueError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotEditingError,
    RecipeNotFoundError,
)
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_add_to_draft,
    get_discard_cart,
    get_get_cart,
    get_remove_from_draft,
    get_replace_draft,
    get_save_cart,
    get_start_cart_edit,
    require_session_ref,
)
from api.schemas.carts import (
    AddDraftItemBody,
    CartDraftBody,
    CartSaveResponse,
    cart_response,
)

router = APIRouter(tags=["cart"])


def _error(status_code: int, code: str, detail: str = "", **extra: object) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code, **extra})


def _run(call: Callable[[], object]) -> object | JSONResponse:
    """Run a use case and map its domain errors (contracts/cart-api.md error table)."""
    try:
        return call()
    except KitchenNotFoundError:
        return _error(status.HTTP_404_NOT_FOUND, "kitchen_not_found", KitchenNotFoundError.MESSAGE)
    except RecipeNotFoundError:
        return _error(
            status.HTTP_404_NOT_FOUND, RecipeNotFoundError.CODE, RecipeNotFoundError.MESSAGE
        )
    except KitchenArchivedError:
        return _error(
            status.HTTP_403_FORBIDDEN, KitchenArchivedError.CODE, KitchenArchivedError.MESSAGE
        )
    except CartLockedError as exc:
        return _error(
            status.HTTP_409_CONFLICT, CartLockedError.CODE, str(exc), editor_alias=exc.editor_alias
        )
    except NotEditingError:
        return _error(status.HTTP_409_CONFLICT, NotEditingError.CODE, NotEditingError.MESSAGE)
    except CartValueError as exc:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT, CartValueError.CODE, str(exc), field=exc.field
        )


def _answer(result: object) -> Response:
    if isinstance(result, Response):
        return result
    assert isinstance(result, CartView)
    return JSONResponse(content=cart_response(result).model_dump(mode="json"))


@router.get("/kitchens/{kitchen_id}/cart")
def get_cart(
    kitchen_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: GetCartService = Depends(get_get_cart),
) -> Response:
    return _answer(_run(lambda: service.execute(ref, kitchen_id)))


@router.post("/kitchens/{kitchen_id}/cart/edit")
def start_cart_edit(
    kitchen_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: StartCartEditService = Depends(get_start_cart_edit),
) -> Response:
    return _answer(_run(lambda: service.execute(ref, kitchen_id)))


@router.put("/kitchens/{kitchen_id}/cart/draft")
def replace_cart_draft(
    kitchen_id: uuid.UUID,
    body: CartDraftBody,
    ref: SessionRef = Depends(require_session_ref),
    service: ReplaceDraftService = Depends(get_replace_draft),
) -> Response:
    items = [(item.recipe_id, item.servings) for item in body.items]
    return _answer(_run(lambda: service.execute(ref, kitchen_id, items)))


@router.post("/kitchens/{kitchen_id}/cart/draft/items")
def add_cart_draft_item(
    kitchen_id: uuid.UUID,
    body: AddDraftItemBody,
    ref: SessionRef = Depends(require_session_ref),
    service: AddToDraftService = Depends(get_add_to_draft),
) -> Response:
    return _answer(_run(lambda: service.execute(ref, kitchen_id, body.recipe_id)))


@router.delete("/kitchens/{kitchen_id}/cart/draft/items/{recipe_id}")
def remove_cart_draft_item(
    kitchen_id: uuid.UUID,
    recipe_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: RemoveFromDraftService = Depends(get_remove_from_draft),
) -> Response:
    return _answer(_run(lambda: service.execute(ref, kitchen_id, recipe_id)))


@router.post("/kitchens/{kitchen_id}/cart/save")
def save_cart(
    kitchen_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: SaveCartService = Depends(get_save_cart),
) -> Response:
    result = _run(lambda: service.execute(ref, kitchen_id))
    if isinstance(result, Response):
        return result
    body = CartSaveResponse(
        **cart_response(result.view).model_dump(),  # type: ignore[union-attr]
        dropped_recipe_ids=list(result.dropped_recipe_ids),  # type: ignore[union-attr]
    )
    return JSONResponse(content=body.model_dump(mode="json"))


@router.delete("/kitchens/{kitchen_id}/cart/edit")
def discard_cart_edit(
    kitchen_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: DiscardCartService = Depends(get_discard_cart),
) -> Response:
    result = _run(lambda: service.execute(ref, kitchen_id))
    if isinstance(result, Response):
        return result
    return Response(status_code=status.HTTP_204_NO_CONTENT)
