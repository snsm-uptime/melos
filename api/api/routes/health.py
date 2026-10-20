"""Health check endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    """Health check endpoint returning status and timestamp."""
    return {
        "status": "healthy",
        "service": "api",
        "timestamp": datetime.now(UTC).isoformat(),
    }
