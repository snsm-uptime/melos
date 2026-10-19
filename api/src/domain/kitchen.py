"""Kitchen domain model"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class MemberRole(str, Enum):
    """Member roles in a kitchen"""
    VISITOR = "visitor"
    MEMBER = "member"
    OWNER = "owner"


@dataclass
class Member:
    """Member of a kitchen"""
    id: UUID
    kitchen_id: UUID
    user_id: UUID
    role: MemberRole
    joined_at: datetime
    is_active: bool = True


@dataclass
class Kitchen:
    """Shared kitchen entity"""
    id: UUID
    name: str
    owner_id: UUID
    content_language: str = "en"
    timezone: str = "UTC"
    members: List[Member] = None

    def __post_init__(self):
        if self.members is None:
            self.members = []

    def get_member(self, user_id: UUID) -> Optional[Member]:
        """Get member by user ID"""
        return next((m for m in self.members if m.user_id == user_id), None)

    def can_manage(self, user_id: UUID) -> bool:
        """Check if user can manage kitchen"""
        member = self.get_member(user_id)
        return member and member.role == MemberRole.OWNER

    def can_edit_recipes(self, user_id: UUID) -> bool:
        """Check if user can edit recipes"""
        member = self.get_member(user_id)
        return member and member.role in (MemberRole.MEMBER, MemberRole.OWNER)

    def can_view(self, user_id: UUID) -> bool:
        """Check if user can view kitchen"""
        return self.get_member(user_id) is not None
