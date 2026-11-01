"""Notebook sharing DTOs (spec 057, contracts/notebook-sharing-api.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SendNotebookInviteRequest(BaseModel):
    email: str = Field(max_length=320)


class NotebookInviteResponse(BaseModel):
    id: UUID
    email: str
    expires_at: datetime
    expired: bool


class NotebookInviteSentResponse(BaseModel):
    status: Literal["sent"]
    invite: NotebookInviteResponse


class NotebookInvitesResponse(BaseModel):
    invites: list[NotebookInviteResponse]


class NotebookMemberResponse(BaseModel):
    user_id: UUID
    alias: str | None
    role: Literal["owner", "member"]
    is_self: bool


class NotebookMembersResponse(BaseModel):
    members: list[NotebookMemberResponse]


class NotebookInvitePreviewResponse(BaseModel):
    notebook_name: str
    inviter_alias: str | None
    email_hint: str


class AcceptNotebookInviteRequest(BaseModel):
    token: str = Field(default="", max_length=512)


class AcceptNotebookInviteResponse(BaseModel):
    notebook_id: UUID
