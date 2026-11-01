"""Notebooks: my notebooks, my default, a kitchen's notebooks and one notebook (spec 056), and
adding a snapshot and the member's own capture notebook in a kitchen (spec 035).

Static segments are declared before /{notebook_id} so "default" and "kitchens" are not
read as ids.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict

from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
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
from application.notebooks import (
    AddNotebookSnapshotCommand,
    AddNotebookSnapshotService,
    GetDefaultNotebookCommand,
    GetDefaultNotebookService,
    GetNotebookCommand,
    GetNotebookService,
    ListKitchenNotebooksCommand,
    ListKitchenNotebooksService,
    ListMyNotebooksCommand,
    ListMyNotebooksService,
    NotebookView,
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
    InvalidPageError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookNotFoundError,
    SnapshotExistsError,
)
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import (
    get_db,
    get_list_kitchen_recipes,
    get_list_notebook_recipes,
    require_authenticated_user,
)
from api.schemas.notebooks import (
    AddNotebookSnapshotRequest,
    NotebookResponse,
    NotebooksResponse,
)
from api.schemas.recipe_lists import RecipePageResponse

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
    "/kitchens/{kitchen_id}/snapshots",
    response_model=NotebookResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_notebook_snapshot(
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
    view = GetNotebookService(SqlAlchemyNotebookRepository(db)).execute(
        GetNotebookCommand(actor_user_id=user_id, notebook_id=captured.notebook_id)
    )
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
