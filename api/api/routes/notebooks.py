"""Notebooks: my notebooks, my default, a kitchen's notebooks and one notebook (spec 056),
adding a snapshot and the member's own capture notebook in a kitchen (spec 035), and creating,
renaming and deleting notebooks (spec 059).

Static segments are declared before /{notebook_id} so "default" and "kitchens" are not
read as ids.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict

from adapters.email import SmtpEmailSender, load_smtp_settings
from adapters.persistence.embeddings import SqlAlchemyEmbeddingJobs
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.notebook_invites import SqlAlchemyNotebookInviteRepository
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
)
from application.notebook_invites import (
    CancelNotebookInviteCommand,
    CancelNotebookInviteService,
    ListNotebookInvitesCommand,
    ListNotebookInvitesService,
    NotebookInviteSent,
    NotebookInviteView,
    ResendNotebookInviteCommand,
    ResendNotebookInviteService,
    SendNotebookInviteCommand,
    SendNotebookInviteService,
)
from application.notebook_members import (
    LeaveNotebookCommand,
    LeaveNotebookService,
    ListNotebookMembersCommand,
    ListNotebookMembersService,
    RemoveNotebookMemberCommand,
    RemoveNotebookMemberService,
)
from application.notebooks import (
    AddNotebookSnapshotCommand,
    AddNotebookSnapshotService,
    CreateKitchenNotebookCommand,
    CreateKitchenNotebookService,
    CreateNotebookCommand,
    CreateNotebookService,
    DeleteNotebookCommand,
    DeleteNotebookService,
    GetDefaultNotebookCommand,
    GetDefaultNotebookService,
    GetNotebookCommand,
    GetNotebookService,
    ListKitchenNotebooksCommand,
    ListKitchenNotebooksService,
    ListMyNotebooksCommand,
    ListMyNotebooksService,
    NotebookView,
    RenameNotebookCommand,
    RenameNotebookService,
    ResolveCaptureNotebookCommand,
    ResolveCaptureNotebookService,
)
from application.recipe_lists import (
    ListKitchenRecipesCommand,
    ListKitchenRecipesService,
    ListNotebookRecipesCommand,
    ListNotebookRecipesService,
    RecipeListResult,
)
from domain.errors import (
    AlreadyInNotebookError,
    InvalidInviteEmailError,
    InvalidNotebookNameError,
    InvalidPageError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookInviteNotFoundError,
    NotebookMemberNotFoundError,
    NotebookNotFoundError,
    NotebookNotShareableError,
    NotebookOwnerOnlyError,
    NotebookOwnerStaysError,
    SmtpConfigurationError,
    SmtpSendError,
    SnapshotExistsError,
)
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import (
    get_auth_settings,
    get_db,
    get_list_kitchen_recipes,
    get_list_notebook_recipes,
    require_authenticated_user,
    require_user_alias,
)
from api.schemas.notebook_invites import (
    NotebookInviteResponse,
    NotebookInviteSentResponse,
    NotebookInvitesResponse,
    NotebookMemberResponse,
    NotebookMembersResponse,
    SendNotebookInviteRequest,
)
from api.schemas.notebooks import (
    AddNotebookSnapshotRequest,
    CreateNotebookRequest,
    NameNotebookRequest,
    NotebookResponse,
    NotebooksResponse,
)
from api.schemas.recipe_lists import RecipePageResponse
from api.settings import AuthSettings
from api.smtp_responses import smtp_error_response
from api.worker import wake_embedding_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

MAX_FILTER_CHARS = 100


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


def _kitchen_archived() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": KitchenArchivedError.MESSAGE, "code": KitchenArchivedError.CODE},
    )


def _invalid_notebook_name() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": InvalidNotebookNameError.MESSAGE,
            "code": InvalidNotebookNameError.CODE,
        },
    )


def _invalid_page() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": InvalidPageError.MESSAGE, "code": InvalidPageError.CODE},
    )


def _invalid_query() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "The filter text is too long.", "code": "invalid_query"},
    )


# The sharing refusals of the contract, each with the same detail and code wherever it arises.
_SharingRefusal = (
    NotebookNotFoundError
    | NotebookNotShareableError
    | NotebookOwnerOnlyError
    | NotebookOwnerStaysError
    | NotebookInviteNotFoundError
    | NotebookMemberNotFoundError
    | AlreadyInNotebookError
)
_SHARING_STATUS: dict[type[_SharingRefusal], int] = {
    NotebookNotFoundError: status.HTTP_404_NOT_FOUND,
    NotebookNotShareableError: status.HTTP_403_FORBIDDEN,
    NotebookOwnerOnlyError: status.HTTP_403_FORBIDDEN,
    NotebookOwnerStaysError: status.HTTP_403_FORBIDDEN,
    NotebookInviteNotFoundError: status.HTTP_404_NOT_FOUND,
    NotebookMemberNotFoundError: status.HTTP_404_NOT_FOUND,
    AlreadyInNotebookError: status.HTTP_409_CONFLICT,
}
_SHARING_REFUSALS = tuple(_SHARING_STATUS)


def _sharing_refused(exc: _SharingRefusal) -> JSONResponse:
    return JSONResponse(
        status_code=_SHARING_STATUS[type(exc)],
        content={"detail": exc.MESSAGE, "code": exc.CODE},
    )


def _invite_response(view: NotebookInviteView) -> NotebookInviteResponse:
    return NotebookInviteResponse(**asdict(view))


def _sent_response(sent: NotebookInviteSent) -> NotebookInviteSentResponse:
    return NotebookInviteSentResponse(status="sent", invite=_invite_response(sent.invite))


def _invite_smtp_failed(
    db: Session, exc: SmtpConfigurationError | SmtpSendError, notebook_id: uuid.UUID
) -> JSONResponse:
    """Undoes the stored invite, so an earlier link keeps working (research R7)."""
    db.rollback()
    logger.error(
        "notebook_invite_smtp_failed notebook_id=%s code=%s", notebook_id, type(exc).__name__
    )
    return smtp_error_response(exc)


def _recipe_page(result: RecipeListResult) -> RecipePageResponse:
    return RecipePageResponse(**asdict(result))


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


@router.post("", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
def create_notebook(
    body: CreateNotebookRequest,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> NotebookResponse | JSONResponse:
    service = CreateNotebookService(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyTransactionCommitter(db),
    )
    try:
        view = service.execute(CreateNotebookCommand(actor_user_id=user_id, name=body.name))
    except InvalidNotebookNameError:
        return _invalid_notebook_name()
    return _response(view)


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


@router.post(
    "/kitchens/{kitchen_id}",
    response_model=NotebookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_kitchen_notebook(
    kitchen_id: uuid.UUID,
    body: NameNotebookRequest,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> NotebookResponse | JSONResponse:
    service = CreateKitchenNotebookService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyTransactionCommitter(db),
    )
    try:
        view = service.execute(
            CreateKitchenNotebookCommand(
                actor_user_id=user_id, kitchen_id=kitchen_id, name=body.name
            )
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    except KitchenArchivedError:
        return _kitchen_archived()
    except InvalidNotebookNameError:
        return _invalid_notebook_name()
    return _response(view)


@router.post(
    "/kitchens/{kitchen_id}/snapshots",
    response_model=NotebookResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_notebook_snapshot(
    request: Request,
    kitchen_id: uuid.UUID,
    body: AddNotebookSnapshotRequest,
    response: Response,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> NotebookResponse | JSONResponse:
    service = AddNotebookSnapshotService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyRecipeRepository(db),
        embedding_jobs=SqlAlchemyEmbeddingJobs(db),
    )
    try:
        added = service.execute(
            AddNotebookSnapshotCommand(
                actor_user_id=user_id,
                kitchen_id=kitchen_id,
                source_notebook_id=body.source_notebook_id,
                snapshot_key=body.snapshot_key,
                confirm_repeat=body.confirm_repeat,
            )
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    except KitchenArchivedError:
        return _kitchen_archived()
    except NotebookNotFoundError:
        return _notebook_not_found()
    except SnapshotExistsError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": SnapshotExistsError.MESSAGE, "code": SnapshotExistsError.CODE},
        )
    if not added.created:
        response.status_code = status.HTTP_200_OK
    else:
        wake_embedding_worker(request.app)
    return _response(added.notebook)


@router.post("/kitchens/{kitchen_id}/capture-notebook", response_model=NotebookResponse)
def resolve_capture_notebook(
    kitchen_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> NotebookResponse | JSONResponse:
    service = ResolveCaptureNotebookService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyUserDefaultNotebook(db),
        SqlAlchemyAuthUserRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyTransactionCommitter(db),
    )
    try:
        captured = service.execute(
            ResolveCaptureNotebookCommand(actor_user_id=user_id, kitchen_id=kitchen_id)
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    except KitchenArchivedError:
        return _kitchen_archived()
    try:
        view = GetNotebookService(SqlAlchemyNotebookRepository(db)).execute(
            GetNotebookCommand(actor_user_id=user_id, notebook_id=captured.notebook_id)
        )
    except NotebookNotFoundError:
        return _notebook_not_found()
    return _response(view)


@router.get("/kitchens/{kitchen_id}/recipes", response_model=RecipePageResponse)
def list_kitchen_recipes(
    kitchen_id: uuid.UUID,
    page: int = Query(default=1),
    q: str = Query(default=""),
    user_id: uuid.UUID = Depends(require_authenticated_user),
    service: ListKitchenRecipesService = Depends(get_list_kitchen_recipes),
) -> RecipePageResponse | JSONResponse:
    if len(q) > MAX_FILTER_CHARS:
        return _invalid_query()
    try:
        result = service.execute(
            ListKitchenRecipesCommand(actor_user_id=user_id, kitchen_id=kitchen_id, page=page, q=q)
        )
    except KitchenNotFoundError:
        return _kitchen_not_found()
    except InvalidPageError:
        return _invalid_page()
    return _recipe_page(result)


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


@router.patch("/{notebook_id}", response_model=NotebookResponse)
def rename_notebook(
    notebook_id: uuid.UUID,
    body: NameNotebookRequest,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> NotebookResponse | JSONResponse:
    service = RenameNotebookService(
        SqlAlchemyNotebookRepository(db), SqlAlchemyTransactionCommitter(db)
    )
    try:
        view = service.execute(
            RenameNotebookCommand(actor_user_id=user_id, notebook_id=notebook_id, name=body.name)
        )
    except KitchenArchivedError:
        return _kitchen_archived()
    except InvalidNotebookNameError:
        return _invalid_notebook_name()
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    return _response(view)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(
    notebook_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> Response:
    service = DeleteNotebookService(
        SqlAlchemyNotebookRepository(db), SqlAlchemyTransactionCommitter(db)
    )
    try:
        service.execute(DeleteNotebookCommand(actor_user_id=user_id, notebook_id=notebook_id))
    except KitchenArchivedError:
        return _kitchen_archived()
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{notebook_id}/recipes", response_model=RecipePageResponse)
def list_notebook_recipes(
    notebook_id: uuid.UUID,
    page: int = Query(default=1),
    q: str = Query(default=""),
    user_id: uuid.UUID = Depends(require_authenticated_user),
    service: ListNotebookRecipesService = Depends(get_list_notebook_recipes),
) -> RecipePageResponse | JSONResponse:
    if len(q) > MAX_FILTER_CHARS:
        return _invalid_query()
    try:
        result = service.execute(
            ListNotebookRecipesCommand(
                actor_user_id=user_id, notebook_id=notebook_id, page=page, q=q
            )
        )
    except NotebookNotFoundError:
        return _notebook_not_found()
    except InvalidPageError:
        return _invalid_page()
    return _recipe_page(result)


@router.get("/{notebook_id}/members", response_model=NotebookMembersResponse)
def list_notebook_members(
    notebook_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> NotebookMembersResponse | JSONResponse:
    service = ListNotebookMembersService(SqlAlchemyNotebookRepository(db))
    try:
        rows = service.execute(
            ListNotebookMembersCommand(actor_user_id=user_id, notebook_id=notebook_id)
        )
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    return NotebookMembersResponse(members=[NotebookMemberResponse(**asdict(row)) for row in rows])


# Declared before /members/{member_id}, or "me" would be read as an id.
@router.delete("/{notebook_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_notebook(
    notebook_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> Response:
    service = LeaveNotebookService(SqlAlchemyNotebookRepository(db))
    try:
        service.execute(LeaveNotebookCommand(actor_user_id=user_id, notebook_id=notebook_id))
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    logger.info("notebook_member_left notebook_id=%s user_id=%s", notebook_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{notebook_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_notebook_member(
    notebook_id: uuid.UUID,
    member_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> Response:
    service = RemoveNotebookMemberService(SqlAlchemyNotebookRepository(db))
    try:
        service.execute(
            RemoveNotebookMemberCommand(
                actor_user_id=user_id, notebook_id=notebook_id, user_id=member_id
            )
        )
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    logger.info("notebook_member_removed notebook_id=%s user_id=%s", notebook_id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{notebook_id}/invites", response_model=NotebookInvitesResponse)
def list_notebook_invites(
    notebook_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> NotebookInvitesResponse | JSONResponse:
    service = ListNotebookInvitesService(
        SqlAlchemyNotebookRepository(db), SqlAlchemyNotebookInviteRepository(db)
    )
    try:
        rows = service.execute(
            ListNotebookInvitesCommand(actor_user_id=user_id, notebook_id=notebook_id)
        )
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    return NotebookInvitesResponse(invites=[_invite_response(row) for row in rows])


@router.post(
    "/{notebook_id}/invites",
    response_model=NotebookInviteSentResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_notebook_invite(
    notebook_id: uuid.UUID,
    body: SendNotebookInviteRequest,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
) -> NotebookInviteSentResponse | JSONResponse:
    users = SqlAlchemyAuthUserRepository(db)
    try:
        # load_smtp_settings inside try: a misconfiguration answers smtp_config_error.
        service = SendNotebookInviteService(
            SqlAlchemyNotebookRepository(db),
            SqlAlchemyNotebookInviteRepository(db),
            users,
            users,
            SmtpEmailSender(load_smtp_settings()),
            public_app_url=settings.public_app_url,
        )
        sent = service.execute(
            SendNotebookInviteCommand(
                actor_user_id=user_id, notebook_id=notebook_id, email=body.email
            )
        )
    except InvalidInviteEmailError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(exc), "code": "invalid_invite_email"},
        )
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    except (SmtpConfigurationError, SmtpSendError) as exc:
        return _invite_smtp_failed(db, exc, notebook_id)
    logger.info("notebook_invite_sent notebook_id=%s invite_id=%s", notebook_id, sent.invite.id)
    return _sent_response(sent)


@router.post("/{notebook_id}/invites/{invite_id}/resend", response_model=NotebookInviteSentResponse)
def resend_notebook_invite(
    notebook_id: uuid.UUID,
    invite_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
) -> NotebookInviteSentResponse | JSONResponse:
    users = SqlAlchemyAuthUserRepository(db)
    try:
        service = ResendNotebookInviteService(
            SqlAlchemyNotebookRepository(db),
            SqlAlchemyNotebookInviteRepository(db),
            users,
            users,
            SmtpEmailSender(load_smtp_settings()),
            public_app_url=settings.public_app_url,
        )
        sent = service.execute(
            ResendNotebookInviteCommand(
                actor_user_id=user_id, notebook_id=notebook_id, invite_id=invite_id
            )
        )
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    except (SmtpConfigurationError, SmtpSendError) as exc:
        return _invite_smtp_failed(db, exc, notebook_id)
    logger.info("notebook_invite_resent notebook_id=%s invite_id=%s", notebook_id, invite_id)
    return _sent_response(sent)


@router.delete("/{notebook_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_notebook_invite(
    notebook_id: uuid.UUID,
    invite_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_alias),
    db: Session = Depends(get_db),
) -> Response:
    service = CancelNotebookInviteService(
        SqlAlchemyNotebookRepository(db), SqlAlchemyNotebookInviteRepository(db)
    )
    try:
        service.execute(
            CancelNotebookInviteCommand(
                actor_user_id=user_id, notebook_id=notebook_id, invite_id=invite_id
            )
        )
    except _SHARING_REFUSALS as exc:
        return _sharing_refused(exc)
    logger.info("notebook_invite_cancelled notebook_id=%s invite_id=%s", notebook_id, invite_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
