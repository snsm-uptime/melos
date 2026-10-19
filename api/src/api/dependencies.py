"""Request/response dependencies and middleware"""
from typing import Optional
from fastapi import Request, Cookie


async def get_session_id(
    melos_session: Optional[str] = Cookie(None)
) -> Optional[str]:
    """Extract session ID from cookie"""
    return melos_session
