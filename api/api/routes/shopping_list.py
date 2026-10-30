"""The kitchen's shopping list (spec 023, contracts/shopping-list-api.md).

Read only. The use case does the access check; this module maps its one error to HTTP.
"""

from __future__ import annotations

import uuid

from application.ports import SessionRef
from application.shopping_list import GetShoppingListService
from domain.errors import KitchenNotFoundError
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from api.deps import get_get_shopping_list, require_session_ref
from api.schemas.shopping_list import shopping_list_response

router = APIRouter(tags=["shopping-list"])


@router.get("/kitchens/{kitchen_id}/shopping-list")
def get_shopping_list(
    kitchen_id: uuid.UUID,
    ref: SessionRef = Depends(require_session_ref),
    service: GetShoppingListService = Depends(get_get_shopping_list),
) -> Response:
    try:
        view = service.execute(ref, kitchen_id)
    except KitchenNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": KitchenNotFoundError.MESSAGE, "code": "kitchen_not_found"},
        )
    return JSONResponse(content=shopping_list_response(view).model_dump(mode="json"))
