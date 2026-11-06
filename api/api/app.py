"""Application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from adapters.persistence.db import get_session_factory
from application.rate_limit import SlidingWindowRateLimiter
from domain.errors import AliasRequiredError, InvalidPhotoError
from fastapi import Depends, FastAPI, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.deps import require_user_alias
from api.routes.admin import router as admin_router
from api.routes.auth import router as auth_router
from api.routes.carts import router as carts_router
from api.routes.health import router as health_router
from api.routes.invites import router as invites_router
from api.routes.kitchens import router as kitchens_router
from api.routes.notebooks import router as notebooks_router
from api.routes.places import router as places_router
from api.routes.recipe_capture import router as recipe_capture_router
from api.routes.recipes import router as recipes_router
from api.routes.shopping_list import router as shopping_list_router
from api.routes.side_panel import router as side_panel_router
from api.settings import load_auth_settings, load_embedding_settings
from api.worker import start_embedding_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the embedding worker thread when it is enabled, and stop it on exit (spec 019)."""
    settings = load_embedding_settings()
    worker = None
    if settings.worker_enabled:
        worker = start_embedding_worker(app, settings, get_session_factory())
    try:
        yield
    finally:
        if worker is not None:
            worker.stop(timeout_s=5.0)
            app.state.embedding_worker = None


def create_app() -> FastAPI:
    application = FastAPI(title="melos-api", version="0.1.0", lifespan=_lifespan)
    application.state.auth_settings = load_auth_settings()
    application.state.rate_limiter = SlidingWindowRateLimiter()

    @application.exception_handler(AliasRequiredError)
    async def _alias_required_handler(_: Request, exc: AliasRequiredError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": AliasRequiredError.CODE},
        )

    @application.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # PatchMeBody.photo_base64 has a wire-level max_length guard so a
        # grossly oversized payload fails fast, before domain.validate_photo()
        # would decode it — but callers still expect the same invalid_photo
        # contract regardless of which layer rejected it.
        for error in exc.errors():
            if error.get("loc", ())[-1:] == ("photo_base64",):
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    content={"detail": InvalidPhotoError.MESSAGE, "code": InvalidPhotoError.CODE},
                )
        return await request_validation_exception_handler(request, exc)

    application.include_router(health_router)
    application.include_router(auth_router)
    # Kitchen chrome needs a person label; invites/auth stay open so the alias can be claimed.
    application.include_router(kitchens_router, dependencies=[Depends(require_user_alias)])
    # A member's default notebook is named after their alias.
    application.include_router(notebooks_router, dependencies=[Depends(require_user_alias)])
    application.include_router(recipe_capture_router, dependencies=[Depends(require_user_alias)])
    application.include_router(recipes_router, dependencies=[Depends(require_user_alias)])
    application.include_router(carts_router, dependencies=[Depends(require_user_alias)])
    application.include_router(shopping_list_router, dependencies=[Depends(require_user_alias)])
    application.include_router(side_panel_router, dependencies=[Depends(require_user_alias)])
    application.include_router(places_router, dependencies=[Depends(require_user_alias)])
    application.include_router(invites_router)
    # Not behind require_user_alias: anyone who is not an admin gets the same 404 (spec 055 R16).
    application.include_router(admin_router)
    return application
