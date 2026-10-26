"""Notebook reads: my notebooks, my default, a kitchen's notebooks and one notebook (spec 056).

Static segments are declared before /{notebook_id} so "default" and "kitchens" are not
read as ids. The capture notebook step has no route (FR-013).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict

from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
)
from application.notebooks import (
    GetDefaultNotebookCommand,
    GetDefaultNotebookService,
    GetNotebookCommand,
    GetNotebookService,
    ListKitchenNotebooksCommand,
    ListKitchenNotebooksService,
    ListMyNotebooksCommand,
    ListMyNotebooksService,
    NotebookView,
)
from domain.errors import KitchenNotFoundError, NotebookNotFoundError
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import get_db, require_authenticated_user
from api.schemas.notebooks import NotebookResponse, NotebooksResponse

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


def _kitchen_not_found() -> JSONResponse:
    """Same body for missing kitchen and non-member — no existence oracle."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": KitchenNotFoundError.MESSAGE, "code": "kitchen_not_found"},
    )


def _notebook_not_found() -> JSONResponse:
    """Same body for a missing notebook and one the caller may not see."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": NotebookNotFoundError.MESSAGE, "code": NotebookNotFoundError.CODE},
    )


def _response(view: NotebookView) -> NotebookResponse:
    return NotebookResponse(**asdict(view))


@router.get("", response_model=NotebooksResponse)
def list_my_notebooks(
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> NotebooksResponse:
    views = ListMyNotebooksService(SqlAlchemyNotebookRepository(db)).execute(
        ListMyNotebooksCommand(actor_user_id=user_id)
    )
    return NotebooksResponse(notebooks=[_response(view) for view in views])


@router.get("/default", response_model=NotebookResponse)
def get_default_notebook(
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> NotebookResponse:
    service = GetDefaultNotebookService(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyUserDefaultNotebook(db),
        SqlAlchemyAuthUserRepository(db),
        SqlAlchemyIngredientCatalog(db),
    )
    view = service.execute(GetDefaultNotebookCommand(actor_user_id=user_id))
    return _response(view)


@router.get("/kitchens/{kitchen_id}", response_model=NotebooksResponse)
def list_kitchen_notebooks(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> NotebooksResponse | JSONResponse:
    service = ListKitchenNotebooksService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyAuthUserRepository(db),
        SqlAlchemyIngredientCatalog(db),
    )
    try:
        views = service.execute(
            ListKitchenNotebooksCommand(actor_user_id=user_id, kitchen_id=kitchen_id)
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    return NotebooksResponse(notebooks=[_response(view) for view in views])


@router.get("/{notebook_id}", response_model=NotebookResponse)
def get_notebook(
    notebook_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> NotebookResponse | JSONResponse:
    service = GetNotebookService(SqlAlchemyNotebookRepository(db))
    try:
        view = service.execute(GetNotebookCommand(actor_user_id=user_id, notebook_id=notebook_id))
    except NotebookNotFoundError:
        return _notebook_not_found()
    return _response(view)
