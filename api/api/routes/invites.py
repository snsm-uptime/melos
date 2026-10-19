"""Invite preview + accept routes (Story 2.4)."""

from __future__ import annotations

import logging
import uuid

from adapters.persistence.email_verification import SqlAlchemyEmailVerificationRepository
from adapters.persistence.kitchen_invite import SqlAlchemyKitchenInviteTokenRepository
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
from domain.errors import (
    EmailNotVerifiedError,
    InvalidInviteTokenError,
    InviteEmailMismatchError,
    KitchenWriteError,
)
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import get_auth_settings, get_db, require_authenticated_user
from api.schemas.invites import (
    AcceptInviteRequest,
    AcceptInviteResponse,
    InvitePreviewResponse,
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
