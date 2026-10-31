"""The kitchen's shopping list (specs 023, 025, contracts/shopping-list-api.md).

The use cases do the access checks and the writes; this module maps their errors to HTTP.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from application.ports import SessionRef
from application.shopping_list import (
    AddShoppingItemService,
    ClosedListView,
    ClosedShoppingListsService,
    CloseShoppingListService,
    GetShoppingListService,
    RemoveShoppingItemService,
)
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    ShoppingDateError,
    ShoppingItemError,
    ShoppingItemNotFoundError,
    ShoppingListEmptyError,
    ShoppingListNotActiveError,
    ShoppingListNotFoundError,
)
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_add_shopping_item,
    get_close_shopping_list,
    get_closed_shopping_lists,
    get_get_shopping_list,
    get_remove_shopping_item,
    require_session_ref,
)
from api.schemas.shopping_list import (
    AddShoppingItemBody,
    CloseShoppingListBody,
    closed_list_response,
    closed_lists_response,
    shopping_list_response,
)

router = APIRouter(tags=["shopping-list"])


def _error(status_code: int, code: str, detail: str, **extra: object) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code, **extra})


def _run(call: Callable[[], object]) -> object | JSONResponse:
    """Run a use case and map its domain errors (contracts/shopping-list-api.md)."""
    try:
        return call()
    except KitchenNotFoundError:
        return _error(status.HTTP_404_NOT_FOUND, "kitchen_not_found", KitchenNotFoundError.MESSAGE)
    except ShoppingListNotFoundError as exc:
        return _error(status.HTTP_404_NOT_FOUND, exc.CODE, exc.MESSAGE)
    except ShoppingItemNotFoundError as exc:
        return _error(status.HTTP_404_NOT_FOUND, exc.CODE, exc.MESSAGE)
    except KitchenArchivedError as exc:
        return _error(status.HTTP_403_FORBIDDEN, exc.CODE, exc.MESSAGE)
    except (ShoppingListNotActiveError, ShoppingListEmptyError) as exc:
        return _error(status.HTTP_409_CONFLICT, exc.CODE, exc.MESSAGE)
    except ShoppingDateError as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.CODE, exc.MESSAGE)
    except ShoppingItemError as exc:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT, exc.CODE, exc.MESSAGE, field=exc.field
        )


def _list_body(
    service: GetShoppingListService,
    ref: SessionRef,
    kitchen_id: uuid.UUID,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    result = _run(lambda: service.execute(ref, kitchen_id))
    if isinstance(result, JSONResponse):
        return result
    return JSONResponse(
        status_code=status_code,
        content=shopping_list_response(result).model_dump(mode="json"),  # type: ignore[arg-type]
    )


@router.get("/kitchens/{kitchen_id}/shopping-list")
def get_shopping_list(
    kitchen_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: GetShoppingListService = Depends(get_get_shopping_list),
) -> Response:
    return _list_body(service, ref, kitchen_id)


@router.post("/kitchens/{kitchen_id}/shopping-list/items")
def add_shopping_item(
    kitchen_id: uuid.UUID,
    body: AddShoppingItemBody,
    ref: SessionRef = Depends(require_session_ref),
    service: AddShoppingItemService = Depends(get_add_shopping_item),
    reader: GetShoppingListService = Depends(get_get_shopping_list),
) -> Response:
    result = _run(
        lambda: service.execute(ref, kitchen_id, body.name, body.quantity, body.unit, body.size)
    )
    if isinstance(result, JSONResponse):
        return result
    return _list_body(reader, ref, kitchen_id, status.HTTP_201_CREATED)


@router.delete("/kitchens/{kitchen_id}/shopping-list/items/{item_id}")
def remove_shopping_item(
    kitchen_id: uuid.UUID,
    item_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: RemoveShoppingItemService = Depends(get_remove_shopping_item),
    reader: GetShoppingListService = Depends(get_get_shopping_list),
) -> Response:
    result = _run(lambda: service.execute(ref, kitchen_id, item_id))
    if isinstance(result, JSONResponse):
        return result
    return _list_body(reader, ref, kitchen_id)


def _closed(result: object) -> Response:
    if isinstance(result, JSONResponse):
        return result
    assert isinstance(result, ClosedListView)
    return JSONResponse(content=closed_list_response(result).model_dump(mode="json"))


@router.post("/kitchens/{kitchen_id}/shopping-list/done")
def close_shopping_list(
    kitchen_id: uuid.UUID,
    body: CloseShoppingListBody,
    ref: SessionRef = Depends(require_session_ref),
    service: CloseShoppingListService = Depends(get_close_shopping_list),
) -> Response:
    return _closed(
        _run(lambda: service.execute(ref, kitchen_id, body.list_id, body.closing_date))
    )


@router.get("/kitchens/{kitchen_id}/shopping-lists")
def list_closed_shopping_lists(
    kitchen_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: ClosedShoppingListsService = Depends(get_closed_shopping_lists),
) -> Response:
    result = _run(lambda: service.list(ref, kitchen_id))
    if isinstance(result, JSONResponse):
        return result
    return JSONResponse(
        content=closed_lists_response(result).model_dump(mode="json")  # type: ignore[arg-type]
    )


@router.get("/kitchens/{kitchen_id}/shopping-lists/{list_id}")
def get_closed_shopping_list(
    kitchen_id: uuid.UUID,
    list_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: ClosedShoppingListsService = Depends(get_closed_shopping_lists),
) -> Response:
    return _closed(_run(lambda: service.get(ref, kitchen_id, list_id)))
