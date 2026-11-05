"""A person's places to buy things (spec 070 contracts/places.md)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from adapters.persistence.places import SqlAlchemyPlaceRepository
from application.places import (
    AddPlaceService,
    CopyPlacesService,
    DeletePlaceService,
    IngredientPlacesService,
    ListPlacesService,
    PlaceSourcesService,
    RenamePlaceService,
    SetIngredientPlaceService,
)
from domain.errors import (
    IngredientNameInvalidError,
    InvalidPlaceError,
    PlaceLimitError,
    PlaceNameInvalidError,
    PlaceNameTakenError,
    PlaceNotFoundError,
)
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.deps import get_db, require_authenticated_user
from api.schemas.places import (
    CopyPlacesBody,
    IngredientPlacesResponse,
    PlaceNameBody,
    PlaceSourceResponse,
    PlaceSourcesResponse,
    SetIngredientPlaceBody,
    ingredient_place_response,
    places_response,
)
from api.schemas.shopping_list import CustomPlaceResponse

router = APIRouter(prefix="/me", tags=["places"])


def _error(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


def _run(db: Session, call: Callable[[], object]) -> object:
    try:
        return call()
    except PlaceNotFoundError as exc:
        return _error(status.HTTP_404_NOT_FOUND, exc.CODE, exc.MESSAGE)
    except (PlaceNameTakenError, PlaceLimitError) as exc:
        return _error(status.HTTP_409_CONFLICT, exc.CODE, exc.MESSAGE)
    except (PlaceNameInvalidError, InvalidPlaceError, IngredientNameInvalidError) as exc:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.CODE, exc.MESSAGE)
    except IntegrityError:
        # Two adds of the same name at once: the unique index decides (research R6).
        db.rollback()
        return _error(
            status.HTTP_409_CONFLICT, PlaceNameTakenError.CODE, PlaceNameTakenError.MESSAGE
        )


def _json(result: object, status_code: int = status.HTTP_200_OK) -> Response:
    if isinstance(result, JSONResponse):
        return result
    assert hasattr(result, "model_dump")
    return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


@router.get("/places")
def list_places(
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    repo = SqlAlchemyPlaceRepository(db)
    return _json(places_response(ListPlacesService(repo).execute(user_id)))


@router.post("/places")
def add_place(
    body: PlaceNameBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    service = AddPlaceService(SqlAlchemyPlaceRepository(db))

    def call() -> CustomPlaceResponse:
        place = service.execute(user_id, body.name)
        db.flush()
        return CustomPlaceResponse(id=place.id, name=place.name)

    return _json(_run(db, call), status.HTTP_201_CREATED)


@router.patch("/places/{place_id}")
def rename_place(
    place_id: uuid.UUID,
    body: PlaceNameBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    service = RenamePlaceService(SqlAlchemyPlaceRepository(db))

    def call() -> CustomPlaceResponse:
        place = service.execute(user_id, place_id, body.name)
        db.flush()
        return CustomPlaceResponse(id=place.id, name=place.name)

    return _json(_run(db, call))


@router.delete("/places/{place_id}")
def delete_place(
    place_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    service = DeletePlaceService(SqlAlchemyPlaceRepository(db))
    result = _run(db, lambda: service.execute(user_id, place_id))
    if isinstance(result, JSONResponse):
        return result
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/ingredient-places")
def list_ingredient_places(
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    items = IngredientPlacesService(SqlAlchemyPlaceRepository(db)).execute(user_id)
    return _json(
        IngredientPlacesResponse(items=[ingredient_place_response(item) for item in items])
    )


@router.put("/ingredient-places")
def set_ingredient_place(
    body: SetIngredientPlaceBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    service = SetIngredientPlaceService(SqlAlchemyPlaceRepository(db))
    result = _run(
        db,
        lambda: ingredient_place_response(service.execute(user_id, body.name, body.place.ref())),
    )
    return _json(result)


@router.get("/place-sources")
def list_place_sources(
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    sources = PlaceSourcesService(SqlAlchemyPlaceRepository(db)).execute(user_id)
    return _json(
        PlaceSourcesResponse(
            items=[PlaceSourceResponse(user_id=s.user_id, alias=s.alias) for s in sources]
        )
    )


@router.post("/places/copy")
def copy_places(
    body: CopyPlacesBody,
    user_id: uuid.UUID = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    service = CopyPlacesService(SqlAlchemyPlaceRepository(db))
    return _json(_run(db, lambda: places_response(service.execute(user_id, body.source_user_id))))
