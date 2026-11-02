"""The response for a failed invite email, shared by the kitchen and notebook routes."""

from __future__ import annotations

from domain.errors import SmtpConfigurationError, SmtpSendError
from fastapi import status
from fastapi.responses import JSONResponse


def smtp_error_response(exc: SmtpConfigurationError | SmtpSendError) -> JSONResponse:
    code = "smtp_config_error" if isinstance(exc, SmtpConfigurationError) else "smtp_send_error"
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc), "code": code},
    )
