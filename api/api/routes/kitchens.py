"""Kitchen create / rename / archive / membership / ACL reads / invites."""

from __future__ import annotations

import logging
import uuid

from adapters.email import SmtpEmailSender, load_smtp_settings
from adapters.persistence.kitchen_invite import SqlAlchemyKitchenInviteTokenRepository
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
)
from application.kitchen_invite import InviteMemberToKitchenCommand, InviteMemberToKitchenService
from application.kitchens import (
    ArchiveKitchenCommand,
    ArchiveKitchenService,
    CreateOwnedKitchenCommand,
    CreateOwnedKitchenService,
    DeleteKitchenCommand,
    DeleteKitchenService,
    GetKitchenDetailCommand,
    GetKitchenDetailService,
    KitchenMembersCommand,
    KitchenMembershipsCommand,
    KitchenMembershipsService,
    KitchenMembersService,
    RenameKitchenCommand,
    RenameKitchenService,
    UnarchiveKitchenCommand,
    UnarchiveKitchenService,
)
from domain.errors import (
    AlreadyKitchenMemberError,
    InvalidInviteEmailError,
    InvalidKitchenNameError,
    KitchenNotFoundError,
    KitchenWriteError,
    NotKitchenMemberError,
    NotKitchenOwnerError,
    SmtpConfigurationError,
    SmtpSendError,
)
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from api.deps import get_auth_settings, get_db, require_authenticated_user
from api.schemas.kitchens import (
    CreateKitchenBody,
    InviteMemberBody,
    InviteMemberResponse,
    KitchenDetailResponse,
    KitchenMemberItem,
    KitchenMembershipItem,
    KitchenMembershipsResponse,
    KitchenMembersResponse,
    KitchenResponse,
    RenameKitchenBody,
)
from api.settings import AuthSettings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kitchens", tags=["kitchens"])


def _kitchen_response(
    kitchen_id: uuid.UUID, name: str, owner_id: uuid.UUID, is_archived: bool = False
) -> KitchenResponse:
    return KitchenResponse(id=kitchen_id, name=name, owner_id=owner_id, is_archived=is_archived)


def _access_denied() -> JSONResponse:
    """Same body for missing kitchen and non-member on mutations — no existence oracle."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": NotKitchenMemberError.MESSAGE, "code": "not_kitchen_member"},
    )


def _kitchen_not_found() -> JSONResponse:
    """Same body for missing kitchen and non-member on reads (Story 1.5.4 disclosure)."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": KitchenNotFoundError.MESSAGE, "code": "kitchen_not_found"},
    )


def _smtp_error_response(exc: SmtpConfigurationError | SmtpSendError) -> JSONResponse:
    code = "smtp_config_error" if isinstance(exc, SmtpConfigurationError) else "smtp_send_error"
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc), "code": code},
    )


@router.get("", response_model=KitchenMembershipsResponse)
def kitchen_memberships(
    archived: bool = Query(default=False),
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenMembershipsResponse:
    service = KitchenMembershipsService(SqlAlchemyKitchenRepository(db))
    items = service.execute(KitchenMembershipsCommand(actor_user_id=user_id, archived=archived))
    return KitchenMembershipsResponse(
        kitchens=[
            KitchenMembershipItem(
                id=item.id,
                name=item.name,
                owner_id=item.owner_id,
                role=item.role,
                is_archived=archived,
                members=[
                    KitchenMemberItem(
                        user_id=member.user_id,
                        alias=member.alias,
                        photo_base64=member.photo_base64,
                    )
                    for member in item.members
                ],
            )
            for item in items
        ]
    )


@router.post("", response_model=KitchenResponse, status_code=status.HTTP_201_CREATED)
def create_kitchen(
    body: CreateKitchenBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenResponse | JSONResponse:
    service = CreateOwnedKitchenService(SqlAlchemyKitchenRepository(db))
    try:
        result = service.execute(CreateOwnedKitchenCommand(actor_user_id=user_id, name=body.name))
    except InvalidKitchenNameError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(exc), "code": "invalid_kitchen_name"},
        )
    except KitchenWriteError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "code": "kitchen_write_failed"},
        )
    logger.info("kitchen_created kitchen_id=%s owner_id=%s", result.id, result.owner_id)
    return _kitchen_response(result.id, result.name, result.owner_id)


@router.get("/{kitchen_id}", response_model=KitchenDetailResponse)
def get_kitchen_detail(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenDetailResponse | JSONResponse:
    service = GetKitchenDetailService(SqlAlchemyKitchenRepository(db))
    try:
        result = service.execute(
            GetKitchenDetailCommand(actor_user_id=user_id, kitchen_id=kitchen_id)
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    return KitchenDetailResponse(
        id=result.id, name=result.name, owner_id=result.owner_id, is_archived=result.is_archived
    )


@router.get("/{kitchen_id}/members", response_model=KitchenMembersResponse)
def get_kitchen_members(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenMembersResponse | JSONResponse:
    service = KitchenMembersService(SqlAlchemyKitchenRepository(db))
    try:
        result = service.execute(
            KitchenMembersCommand(actor_user_id=user_id, kitchen_id=kitchen_id)
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    return KitchenMembersResponse(
        members=[
            KitchenMemberItem(user_id=m.user_id, alias=m.alias, photo_base64=m.photo_base64)
            for m in result.members
        ]
    )


@router.post(
    "/{kitchen_id}/invites",
    response_model=InviteMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    kitchen_id: uuid.UUID,
    body: InviteMemberBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
) -> InviteMemberResponse | JSONResponse:
    kitchen_repo = SqlAlchemyKitchenRepository(db)
    users = SqlAlchemyAuthUserRepository(db)
    try:
        # load_smtp_settings inside try — misconfig must be 503 smtp_config_error (AC #5).
        service = InviteMemberToKitchenService(
            kitchen_repo,
            users,
            users,
            SqlAlchemyKitchenInviteTokenRepository(db),
            SmtpEmailSender(load_smtp_settings()),
            public_app_url=settings.public_app_url,
        )
        result = service.execute(
            InviteMemberToKitchenCommand(
                actor_user_id=user_id,
                kitchen_id=kitchen_id,
                email=body.email,
            )
        )
    except InvalidInviteEmailError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(exc), "code": "invalid_invite_email"},
        )
    except AlreadyKitchenMemberError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "code": "already_kitchen_member"},
        )
    except (KitchenNotFoundError, NotKitchenMemberError):
        return _kitchen_not_found()
    except NotKitchenOwnerError as exc:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "not_kitchen_owner"},
        )
    except (SmtpConfigurationError, SmtpSendError) as exc:
        db.rollback()
        logger.error(
            "kitchen_invite_smtp_failed kitchen_id=%s code=%s",
            kitchen_id,
            type(exc).__name__,
        )
        return _smtp_error_response(exc)

    logger.info(
        "kitchen_invite_sent kitchen_id=%s invite_id=%s template=%s",
        kitchen_id,
        result.invite_id,
        result.template_kind,
    )
    return InviteMemberResponse(
        status=result.status,
        template_kind=result.template_kind,
        invite_id=result.invite_id,
    )


@router.patch("/{kitchen_id}", response_model=KitchenResponse)
def rename_kitchen(
    kitchen_id: uuid.UUID,
    body: RenameKitchenBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenResponse | JSONResponse:
    service = RenameKitchenService(SqlAlchemyKitchenRepository(db))
    try:
        result = service.execute(
            RenameKitchenCommand(
                actor_user_id=user_id,
                kitchen_id=kitchen_id,
                name=body.name,
            )
        )
    except InvalidKitchenNameError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(exc), "code": "invalid_kitchen_name"},
        )
    except (KitchenNotFoundError, NotKitchenMemberError):
        return _kitchen_not_found()
    except NotKitchenOwnerError as exc:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "not_kitchen_owner"},
        )
    logger.info("kitchen_renamed kitchen_id=%s", result.id)
    return _kitchen_response(result.id, result.name, result.owner_id, result.is_archived)


@router.post("/{kitchen_id}/archive", response_model=KitchenResponse)
def archive_kitchen(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenResponse | JSONResponse:
    service = ArchiveKitchenService(SqlAlchemyKitchenRepository(db))
    try:
        result = service.execute(
            ArchiveKitchenCommand(actor_user_id=user_id, kitchen_id=kitchen_id)
        )
    except (KitchenNotFoundError, NotKitchenMemberError):
        return _kitchen_not_found()
    except NotKitchenOwnerError as exc:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "not_kitchen_owner"},
        )
    logger.info("kitchen_archived kitchen_id=%s", result.id)
    return _kitchen_response(result.id, result.name, result.owner_id, result.is_archived)


@router.post("/{kitchen_id}/unarchive", response_model=KitchenResponse)
def unarchive_kitchen(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> KitchenResponse | JSONResponse:
    service = UnarchiveKitchenService(SqlAlchemyKitchenRepository(db))
    try:
        result = service.execute(
            UnarchiveKitchenCommand(actor_user_id=user_id, kitchen_id=kitchen_id)
        )
    except (KitchenNotFoundError, NotKitchenMemberError):
        return _kitchen_not_found()
    except NotKitchenOwnerError as exc:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "not_kitchen_owner"},
        )
    logger.info("kitchen_unarchived kitchen_id=%s", result.id)
    return _kitchen_response(result.id, result.name, result.owner_id, result.is_archived)


@router.delete("/{kitchen_id}", response_model=None)
def delete_kitchen(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response | JSONResponse:
    service = DeleteKitchenService(SqlAlchemyKitchenRepository(db))
    try:
        service.execute(DeleteKitchenCommand(actor_user_id=user_id, kitchen_id=kitchen_id))
    except (KitchenNotFoundError, NotKitchenMemberError):
        return _kitchen_not_found()
    except NotKitchenOwnerError as exc:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "not_kitchen_owner"},
        )
    logger.info("kitchen_deleted kitchen_id=%s", kitchen_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
