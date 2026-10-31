"""The side panel's default kitchen and recipe count (spec 064)."""

from __future__ import annotations

import uuid

from adapters.persistence.side_panel import SqlAlchemySidePanelRepository
from application.side_panel import GetSidePanelService, SetDefaultKitchenService, SidePanelView
from domain.errors import KitchenArchivedError, KitchenNotFoundError
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import get_db, require_authenticated_user
from api.schemas.side_panel import SetDefaultKitchenBody, SidePanelResponse

router = APIRouter(prefix="/side-panel", tags=["side-panel"])


def _response(view: SidePanelView) -> SidePanelResponse:
    return SidePanelResponse(
        default_kitchen_id=view.default_kitchen_id, recipes_added=view.recipes_added
    )


@router.get("", response_model=SidePanelResponse)
def side_panel(
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> SidePanelResponse:
    return _response(GetSidePanelService(SqlAlchemySidePanelRepository(db)).execute(user_id))


@router.put("/default-kitchen", response_model=SidePanelResponse)
def set_default_kitchen(
    body: SetDefaultKitchenBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> SidePanelResponse | JSONResponse:
    service = SetDefaultKitchenService(SqlAlchemySidePanelRepository(db))
    try:
        return _response(service.execute(user_id, body.kitchen_id))
    except KitchenNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": KitchenNotFoundError.MESSAGE, "code": "kitchen_not_found"},
        )
    except KitchenArchivedError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "This kitchen is archived.", "code": KitchenArchivedError.CODE},
        )
