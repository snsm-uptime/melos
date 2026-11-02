"""Invite preview + accept routes (Story 2.4)."""

from __future__ import annotations

import logging
import uuid

from adapters.persistence.email_verification import SqlAlchemyEmailVerificationRepository
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.kitchen_invite import SqlAlchemyKitchenInviteTokenRepository
from adapters.persistence.notebook_invites import SqlAlchemyNotebookInviteRepository
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
)
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
)
from application.kitchen_invite_accept import (
    AcceptKitchenInviteCommand,
    AcceptKitchenInviteService,
    PreviewKitchenInviteCommand,
    PreviewKitchenInviteService,
)
from application.notebook_invites import (
    AcceptNotebookInviteCommand,
    AcceptNotebookInviteService,
    PreviewNotebookInviteCommand,
    PreviewNotebookInviteService,
)
from domain.errors import (
    EmailNotVerifiedError,
    InvalidInviteTokenError,
    InviteEmailMismatchError,
    KitchenWriteError,
)
from domain.notebook_invite import INVALID_NOTEBOOK_INVITE_MESSAGE
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import (
    get_auth_settings,
    get_db,
    require_authenticated_user,
    require_user_alias,
)
from api.schemas.invites import (
    AcceptInviteRequest,
    AcceptInviteResponse,
    InvitePreviewResponse,
)
from api.schemas.notebook_invites import (
    AcceptNotebookInviteRequest,
    AcceptNotebookInviteResponse,
    NotebookInvitePreviewResponse,
)
from api.settings import AuthSettings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["invites"])


def _invalid_invite_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": InvalidInviteTokenError.MESSAGE,
            "code": InvalidInviteTokenError.CODE,
        },
    )


@router.get("/preview", response_model=InvitePreviewResponse)
def preview_invite(
    token: str = Query(default=""),
    db: Session = Depends(get_db),
) -> InvitePreviewResponse | JSONResponse:
    if not token.strip():
        return _invalid_invite_response()
    service = PreviewKitchenInviteService(
        SqlAlchemyKitchenInviteTokenRepository(db),
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyAuthUserRepository(db),
    )
    try:
        result = service.execute(PreviewKitchenInviteCommand(raw_token=token))
    except InvalidInviteTokenError:
        return _invalid_invite_response()
    return InvitePreviewResponse(
        kitchen_name=result.kitchen_name,
        email_hint=result.email_hint,
        path=result.path,  # type: ignore[arg-type]
    )


@router.post("/accept", response_model=AcceptInviteResponse)
def accept_invite(
    body: AcceptInviteRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(require_authenticated_user),
    settings: AuthSettings = Depends(get_auth_settings),
) -> AcceptInviteResponse | JSONResponse:
    service = AcceptKitchenInviteService(
        SqlAlchemyKitchenInviteTokenRepository(db),
        SqlAlchemyAuthUserRepository(db),
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyEmailVerificationRepository(db),
    )
    try:
        result = service.execute(
            AcceptKitchenInviteCommand(
                actor_user_id=user_id,
                raw_token=body.token,
                email_verification_required=settings.email_verification_required,
            )
        )
    except InvalidInviteTokenError:
        return _invalid_invite_response()
    except InviteEmailMismatchError as exc:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": InviteEmailMismatchError.CODE},
        )
    except EmailNotVerifiedError as exc:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "email_not_verified"},
        )
    except KitchenWriteError:
        return _invalid_invite_response()
    logger.info(
        "invite_accepted user_id=%s kitchen_id=%s already_member=%s",
        user_id,
        result.kitchen_id,
        result.already_member,
    )
    return AcceptInviteResponse(kitchen_id=result.kitchen_id)


def _invalid_notebook_invite() -> JSONResponse:
    """The one body of every dead link (spec 057 SC-006)."""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": INVALID_NOTEBOOK_INVITE_MESSAGE,
            "code": InvalidInviteTokenError.CODE,
        },
    )


@router.get("/notebook/preview", response_model=NotebookInvitePreviewResponse)
def preview_notebook_invite(
    token: str = Query(default=""),
    db: Session = Depends(get_db),
) -> NotebookInvitePreviewResponse | JSONResponse:
    if not token.strip():
        return _invalid_notebook_invite()
    service = PreviewNotebookInviteService(
        SqlAlchemyNotebookInviteRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyAuthUserRepository(db),
    )
    try:
        result = service.execute(PreviewNotebookInviteCommand(raw_token=token))
    except InvalidInviteTokenError:
        return _invalid_notebook_invite()
    return NotebookInvitePreviewResponse(
        notebook_name=result.notebook_name,
        inviter_alias=result.inviter_alias,
        email_hint=result.email_hint,
    )


@router.post("/notebook/accept", response_model=AcceptNotebookInviteResponse)
def accept_notebook_invite(
    body: AcceptNotebookInviteRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(require_user_alias),
    settings: AuthSettings = Depends(get_auth_settings),
) -> AcceptNotebookInviteResponse | JSONResponse:
    """Every error branch rolls back: get_db commits after a route returns a response, even an
    error one, so a claimed token could otherwise be kept without a membership (research R4).
    """
    service = AcceptNotebookInviteService(
        SqlAlchemyNotebookInviteRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyAuthUserRepository(db),
        SqlAlchemyEmailVerificationRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyTransactionCommitter(db),
    )
    try:
        result = service.execute(
            AcceptNotebookInviteCommand(
                actor_user_id=user_id,
                raw_token=body.token,
                email_verification_required=settings.email_verification_required,
            )
        )
    except InvalidInviteTokenError:
        db.rollback()
        return _invalid_notebook_invite()
    except InviteEmailMismatchError as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": InviteEmailMismatchError.CODE},
        )
    except EmailNotVerifiedError as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "email_not_verified"},
        )
    logger.info(
        "notebook_invite_accepted user_id=%s notebook_id=%s already_member=%s",
        user_id,
        result.notebook_id,
        result.already_member,
    )
    return AcceptNotebookInviteResponse(notebook_id=result.notebook_id)
