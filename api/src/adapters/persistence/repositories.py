"""Repository implementations for data persistence"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from api.src.adapters.persistence.models import (
    Kitchen,
    Recipe,
    Ingredient,
    Category,
    Member,
    ShoppingList,
    Invite,
    Recipe as RecipeModel,
)


class KitchenRepository:
    """Kitchen persistence operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, kitchen: Kitchen) -> UUID:
        """Create new kitchen"""
        db_kitchen = Kitchen(**kitchen.dict(exclude_unset=True))
        self.db.add(db_kitchen)
        self.db.commit()
        self.db.refresh(db_kitchen)
        return db_kitchen.id

    async def get(self, kitchen_id: UUID) -> Optional[Kitchen]:
        """Get kitchen by ID"""
        return self.db.query(Kitchen).filter(Kitchen.id == kitchen_id).first()

    async def list_by_owner(self, owner_id: UUID) -> List[Kitchen]:
        """List kitchens owned by user"""
        return self.db.query(Kitchen).filter(Kitchen.owner_id == owner_id).all()


class RecipeRepository:
    """Recipe persistence operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, recipe: RecipeModel) -> UUID:
        """Create new recipe"""
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)
        return recipe.id

    async def get(self, recipe_id: UUID, kitchen_id: UUID) -> Optional[RecipeModel]:
        """Get recipe by ID (kitchen-scoped)"""
        return self.db.query(RecipeModel).filter(
            RecipeModel.id == recipe_id,
            RecipeModel.kitchen_id == kitchen_id,
            RecipeModel.is_deleted == False
        ).first()

    async def list_by_kitchen(self, kitchen_id: UUID) -> List[RecipeModel]:
        """List recipes in kitchen"""
        return self.db.query(RecipeModel).filter(
            RecipeModel.kitchen_id == kitchen_id,
            RecipeModel.is_deleted == False
        ).all()

    async def delete(self, recipe_id: UUID, kitchen_id: UUID) -> bool:
        """Soft-delete recipe"""
        recipe = await self.get(recipe_id, kitchen_id)
        if recipe:
            recipe.is_deleted = True
            self.db.commit()
            return True
        return False


class IngredientRepository:
    """Ingredient persistence operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, ingredient: Ingredient) -> UUID:
        """Create new ingredient"""
        self.db.add(ingredient)
        self.db.commit()
        self.db.refresh(ingredient)
        return ingredient.id

    async def get(self, ingredient_id: UUID, kitchen_id: UUID) -> Optional[Ingredient]:
        """Get ingredient by ID (kitchen-scoped)"""
        return self.db.query(Ingredient).filter(
            Ingredient.id == ingredient_id,
            Ingredient.kitchen_id == kitchen_id
        ).first()

    async def list_by_kitchen(self, kitchen_id: UUID) -> List[Ingredient]:
        """List ingredients in kitchen"""
        return self.db.query(Ingredient).filter(
            Ingredient.kitchen_id == kitchen_id
        ).all()


class MemberRepository:
    """Member persistence operations"""

    def __init__(self, db: Session):
        self.db = db

    async def list_by_kitchen(self, kitchen_id: UUID) -> List[Member]:
        """List members in kitchen"""
        return self.db.query(Member).filter(
            Member.kitchen_id == kitchen_id,
            Member.is_active == True
        ).all()

    async def get_member(self, kitchen_id: UUID, user_id: UUID) -> Optional[Member]:
        """Get member by user ID"""
        return self.db.query(Member).filter(
            Member.kitchen_id == kitchen_id,
            Member.user_id == user_id,
            Member.is_active == True
        ).first()


class ShoppingListRepository:
    """Shopping list persistence operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, shopping_list: ShoppingList) -> UUID:
        """Create new shopping list"""
        self.db.add(shopping_list)
        self.db.commit()
        self.db.refresh(shopping_list)
        return shopping_list.id

    async def get(self, shopping_list_id: UUID, kitchen_id: UUID) -> Optional[ShoppingList]:
        """Get shopping list by ID (kitchen-scoped)"""
        return self.db.query(ShoppingList).filter(
            ShoppingList.id == shopping_list_id,
            ShoppingList.kitchen_id == kitchen_id
        ).first()

    async def list_by_kitchen(self, kitchen_id: UUID) -> List[ShoppingList]:
        """List shopping lists in kitchen"""
        return self.db.query(ShoppingList).filter(
            ShoppingList.kitchen_id == kitchen_id
        ).order_by(ShoppingList.created_at.desc()).all()


class InviteRepository:
    """Invite persistence operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, invite: Invite) -> UUID:
        """Create new invite"""
        self.db.add(invite)
        self.db.commit()
        self.db.refresh(invite)
        return invite.id

    async def get_by_token(self, token: str) -> Optional[Invite]:
        """Get invite by token"""
        return self.db.query(Invite).filter(
            Invite.token == token,
            Invite.accepted == False,
            Invite.expires_at > datetime.utcnow()
        ).first()

    async def list_by_kitchen(self, kitchen_id: UUID) -> List[Invite]:
        """List pending invites for kitchen"""
        return self.db.query(Invite).filter(
            Invite.kitchen_id == kitchen_id,
            Invite.accepted == False,
            Invite.expires_at > datetime.utcnow()
        ).all()

    async def accept(self, token: str) -> bool:
        """Mark invite as accepted"""
        invite = await self.get_by_token(token)
        if invite:
            invite.accepted = True
            self.db.commit()
            return True
        return False
