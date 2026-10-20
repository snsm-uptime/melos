"""Pydantic DTOs for kitchen create / rename / membership / detail / invites."""

from __future__ import annotations

from uuid import UUID

from domain.kitchens import KITCHEN_NAME_MAX_LENGTH
from pydantic import BaseModel, Field


class CreateKitchenBody(BaseModel):
    # Domain validates blank/whitespace via InvalidKitchenNameError for a stable
    # `invalid_kitchen_name` code; wire only caps length to match DB String(200).
    name: str = Field(max_length=KITCHEN_NAME_MAX_LENGTH)
    content_language: str = "en"  # Owner can set language; default "en"


class RenameKitchenBody(BaseModel):
    name: str = Field(max_length=KITCHEN_NAME_MAX_LENGTH)
    content_language: str | None = None  # Optional owner-only update


class KitchenResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    is_archived: bool = False
    content_language: str = "en"


class KitchenMemberItem(BaseModel):
    """Roster label is the alias — email never leaves the invite/auth surfaces."""

    user_id: UUID
    alias: str | None = None
    photo_base64: str | None = None


class KitchenMembershipItem(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    role: str
    members: list[KitchenMemberItem] = Field(default_factory=list)
    is_archived: bool = False
    content_language: str = "en"


class KitchenMembershipsResponse(BaseModel):
    kitchens: list[KitchenMembershipItem]


class KitchenDetailResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    is_archived: bool = False


class KitchenMembersResponse(BaseModel):
    members: list[KitchenMemberItem]


class InviteMemberBody(BaseModel):
    email: str = Field(max_length=320)


class InviteMemberResponse(BaseModel):
    status: str
    template_kind: str
    invite_id: UUID
