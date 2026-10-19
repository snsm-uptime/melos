"""Kitchen management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

router = APIRouter(
    prefix="/kitchens",
    tags=["kitchens"],
)


@router.get("/{kitchen_id}")
async def get_kitchen(kitchen_id: UUID):
    """Get kitchen details"""
    # TODO: Implement with repository
    return {"id": kitchen_id, "name": "My Kitchen"}


@router.get("")
async def list_kitchens():
    """List user's kitchens"""
    # TODO: Implement with repository
    return {"kitchens": []}


@router.post("")
async def create_kitchen(name: str):
    """Create new kitchen"""
    # TODO: Implement with repository
    return {"id": "...", "name": name}
