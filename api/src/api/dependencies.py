"""Request/response dependencies and middleware"""
from typing import Optional
from fastapi import Request, Cookie, HTTPException, status
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class SessionUser:
    """Current session user"""
    def __init__(self, user_id: UUID, email: str):
        self.user_id = user_id
        self.email = email


async def get_session_id(
    melos_session: Optional[str] = Cookie(None)
) -> Optional[str]:
    """Extract session ID from cookie"""
    return melos_session


async def get_current_user(
    melos_session: Optional[str] = Cookie(None)
) -> Optional[SessionUser]:
    """Get current user from session cookie"""
    if not melos_session:
        return None

    # TODO: Validate session token and fetch user
    # For now, return None to allow testing
    return None


async def require_user(user: Optional[SessionUser] = None) -> SessionUser:
    """Require authenticated user"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


class ErrorResponse:
    """Standardized error response"""
    def __init__(self, error_code: str, message: str, details: Optional[dict] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }
