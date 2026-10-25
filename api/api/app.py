"""Application factory."""

from __future__ import annotations

import logging

from application.rate_limit import SlidingWindowRateLimiter
from domain.errors import AliasRequiredError, InvalidPhotoError
from fastapi import Depends, FastAPI, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.deps import require_user_alias
from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.invites import router as invites_router
from api.routes.kitchens import router as kitchens_router
from api.routes.notebooks import router as notebooks_router
from api.settings import load_auth_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def create_app() -> FastAPI:
    application = FastAPI(title="melos-api", version="0.1.0")
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
    application.include_router(invites_router)
    return application
