"""Notebook reads: a kitchen's notebook and a member's own notebooks (spec 055)."""

from __future__ import annotations

import uuid

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
    GetKitchenNotebookCommand,
    GetKitchenNotebookService,
    GetMemberNotebookCommand,
    GetMemberNotebookService,
)
from domain.errors import KitchenNotFoundError, NotebookNotFoundError
from domain.notebook import Notebook
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import get_db, require_authenticated_user
from api.schemas.notebooks import KitchenNotebookResponse, MemberNotebookResponse

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


def _kitchen_not_found() -> JSONResponse:
    """Same body for missing kitchen and non-member — no existence oracle."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": KitchenNotFoundError.MESSAGE, "code": "kitchen_not_found"},
    )


def _notebook_not_found() -> JSONResponse:
    """Same body for a missing notebook and another member's notebook."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": NotebookNotFoundError.MESSAGE, "code": NotebookNotFoundError.CODE},
    )


def _member_response(notebook: Notebook) -> MemberNotebookResponse:
    assert notebook.user_id is not None
    return MemberNotebookResponse(id=notebook.id, user_id=notebook.user_id)


@router.get("/kitchens/{kitchen_id}", response_model=KitchenNotebookResponse)
def get_kitchen_notebook(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenNotebookResponse | JSONResponse:
    service = GetKitchenNotebookService(
        SqlAlchemyKitchenRepository(db), SqlAlchemyNotebookRepository(db)
    )
    try:
        view = service.execute(
            GetKitchenNotebookCommand(actor_user_id=user_id, kitchen_id=kitchen_id)
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    return KitchenNotebookResponse(
        id=view.notebook.id,
        kitchen_id=kitchen_id,
        name=view.kitchen_name,
        is_archived=view.is_archived,
    )


@router.get("/members/{member_id}", response_model=MemberNotebookResponse)
def get_default_notebook(
    member_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> MemberNotebookResponse | JSONResponse:
    service = GetDefaultNotebookService(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyUserDefaultNotebook(db),
        SqlAlchemyAuthUserRepository(db),
    )
    try:
        notebook = service.execute(
            GetDefaultNotebookCommand(actor_user_id=user_id, user_id=member_id)
        )
    except NotebookNotFoundError:
        return _notebook_not_found()
    return _member_response(notebook)


@router.get("/members/{member_id}/{notebook_id}", response_model=MemberNotebookResponse)
def get_member_notebook(
    member_id: uuid.UUID,
    notebook_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> MemberNotebookResponse | JSONResponse:
    service = GetMemberNotebookService(SqlAlchemyNotebookRepository(db))
    try:
        notebook = service.execute(
            GetMemberNotebookCommand(
                actor_user_id=user_id, user_id=member_id, notebook_id=notebook_id
            )
        )
    except NotebookNotFoundError:
        return _notebook_not_found()
    return _member_response(notebook)
