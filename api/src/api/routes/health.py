"""Health check endpoint"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint for liveness probes"""
    return {"status": "healthy", "service": "melos-api"}
