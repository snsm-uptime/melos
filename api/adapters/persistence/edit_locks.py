"""Cart and recipe edit locks (spec 022 research R3, R4, R5, R10, R11).

A lock row counts only while it is live: its session exists and has not expired, its holder
was active within LOCK_IDLE, and the holder may still write. Each holder read is one query.
`resolve_session_ref` reads the session row itself, so `sessions.py` stays as it is.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from application.ports import CartDraft, CartDraftItem, LockAccess, LockHolder, SessionRef
from domain.cart import LOCK_IDLE
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    CartEditLockModel,
    CartModel,
    KitchenMembershipModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeEditLockModel,
    RecipeModel,
    SessionModel,
    UserModel,
)


def resolve_session_ref(db: Session, token: str | None) -> SessionRef | None:
    if not token:
        return None
    row = db.execute(
        select(SessionModel.user_id, SessionModel.id).where(
            SessionModel.token == token, SessionModel.expires_at > func.now()
        )
    ).first()
    if row is None:
        return None
    return SessionRef(user_id=row[0], session_id=row[1])


def draft_to_json(draft: CartDraft) -> dict:
    return {
        "people": draft.people,
        "items": [{"recipe_id": str(i.recipe_id), "meals": i.meals} for i in draft.items],
    }


def draft_from_json(data: dict) -> CartDraft:
    return CartDraft(
        people=data.get("people"),
        items=tuple(
            CartDraftItem(recipe_id=uuid.UUID(i["recipe_id"]), meals=int(i["meals"]))
            for i in data.get("items", [])
        ),
    )


def _cart_id(kitchen_id: uuid.UUID):
    return select(CartModel.id).where(CartModel.kitchen_id == kitchen_id).scalar_subquery()


def _fresh(column):
    return column > func.now() - LOCK_IDLE


class SqlAlchemyEditLockRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def now(self) -> datetime:
        return self._db.scalar(select(func.now()))

    # --- cart -----------------------------------------------------------------------------

    def _live_cart(self, kitchen_id: uuid.UUID):
        lock = CartEditLockModel
        return (
            select(lock, UserModel.alias)
            .join(CartModel, CartModel.id == lock.cart_id)
            .join(SessionModel, SessionModel.id == lock.session_id)
            .join(KitchenMembershipModel, KitchenMembershipModel.id == lock.membership_id)
            .join(KitchenModel, KitchenModel.id == CartModel.kitchen_id)
            .outerjoin(UserModel, UserModel.id == lock.user_id)
            .where(
                CartModel.kitchen_id == kitchen_id,
                KitchenMembershipModel.kitchen_id == kitchen_id,
                SessionModel.expires_at > func.now(),
                _fresh(lock.last_active_at),
                KitchenModel.is_archived.is_(False),
            )
        )

    def cart_holder(self, kitchen_id: uuid.UUID) -> LockHolder | None:
        row = self._db.execute(self._live_cart(kitchen_id)).first()
        if row is None:
            return None
        lock, alias = row
        return LockHolder(lock.session_id, lock.user_id, alias, lock.last_active_at)

    def cart_draft(self, kitchen_id: uuid.UUID, session_id: uuid.UUID) -> CartDraft | None:
        row = self._db.execute(
            self._live_cart(kitchen_id).where(CartEditLockModel.session_id == session_id)
        ).first()
        return None if row is None else draft_from_json(row[0].draft)

    def take_cart(
        self,
        kitchen_id: uuid.UUID,
        ref: SessionRef,
        membership_id: uuid.UUID,
        draft: CartDraft,
    ) -> None:
        cart_id = self._db.scalar(select(CartModel.id).where(CartModel.kitchen_id == kitchen_id))
        values = {
            "session_id": ref.session_id,
            "user_id": ref.user_id,
            "membership_id": membership_id,
            "acquired_at": func.now(),
            "last_active_at": func.now(),
            "draft": draft_to_json(draft),
        }
        stmt = insert(CartEditLockModel).values(cart_id=cart_id, **values)
        self._db.execute(stmt.on_conflict_do_update(index_elements=["cart_id"], set_=values))

    def touch_cart(self, kitchen_id: uuid.UUID, session_id: uuid.UUID) -> None:
        self._db.execute(
            update(CartEditLockModel)
            .where(
                CartEditLockModel.cart_id == _cart_id(kitchen_id),
                CartEditLockModel.session_id == session_id,
            )
            .values(last_active_at=func.now())
        )

    def set_cart_draft(
        self, kitchen_id: uuid.UUID, session_id: uuid.UUID, draft: CartDraft
    ) -> None:
        self._db.execute(
            update(CartEditLockModel)
            .where(
                CartEditLockModel.cart_id == _cart_id(kitchen_id),
                CartEditLockModel.session_id == session_id,
            )
            .values(last_active_at=func.now(), draft=draft_to_json(draft))
        )

    def kitchen_membership_id(self, kitchen_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID | None:
        return self._db.scalar(
            select(KitchenMembershipModel.id).where(
                KitchenMembershipModel.kitchen_id == kitchen_id,
                KitchenMembershipModel.user_id == user_id,
            )
        )

    def release_cart(self, kitchen_id: uuid.UUID, session_id: uuid.UUID) -> None:
        self._db.execute(
            delete(CartEditLockModel).where(
                CartEditLockModel.cart_id == _cart_id(kitchen_id),
                CartEditLockModel.session_id == session_id,
            )
        )

    # --- recipe ---------------------------------------------------------------------------

    def recipe_holder(self, recipe_id: uuid.UUID) -> LockHolder | None:
        lock = RecipeEditLockModel
        kitchen_ok = and_(
            lock.kitchen_membership_id.is_not(None),
            KitchenMembershipModel.kitchen_id == NotebookModel.kitchen_id,
            KitchenModel.is_archived.is_(False),
        )
        personal_ok = and_(
            lock.notebook_id.is_not(None),
            lock.notebook_id == NotebookModel.id,
            NotebookModel.kitchen_id.is_(None),
        )
        row = self._db.execute(
            select(lock, UserModel.alias)
            .join(RecipeModel, RecipeModel.id == lock.recipe_id)
            .join(NotebookModel, NotebookModel.id == RecipeModel.notebook_id)
            .join(SessionModel, SessionModel.id == lock.session_id)
            .outerjoin(
                KitchenMembershipModel, KitchenMembershipModel.id == lock.kitchen_membership_id
            )
            .outerjoin(KitchenModel, KitchenModel.id == KitchenMembershipModel.kitchen_id)
            .outerjoin(UserModel, UserModel.id == lock.user_id)
            .where(
                lock.recipe_id == recipe_id,
                SessionModel.expires_at > func.now(),
                _fresh(lock.last_active_at),
                or_(kitchen_ok, personal_ok),
            )
        ).first()
        if row is None:
            return None
        found, alias = row
        return LockHolder(found.session_id, found.user_id, alias, found.last_active_at)

    def take_recipe(self, recipe_id: uuid.UUID, ref: SessionRef, access: LockAccess) -> None:
        values = {
            "session_id": ref.session_id,
            "user_id": ref.user_id,
            "kitchen_membership_id": access.kitchen_membership_id,
            "notebook_id": access.notebook_id,
            "acquired_at": func.now(),
            "last_active_at": func.now(),
        }
        stmt = insert(RecipeEditLockModel).values(recipe_id=recipe_id, **values)
        self._db.execute(stmt.on_conflict_do_update(index_elements=["recipe_id"], set_=values))

    def touch_recipe(self, recipe_id: uuid.UUID, session_id: uuid.UUID) -> None:
        self._db.execute(
            update(RecipeEditLockModel)
            .where(
                RecipeEditLockModel.recipe_id == recipe_id,
                RecipeEditLockModel.session_id == session_id,
            )
            .values(last_active_at=func.now())
        )

    def release_recipe(self, recipe_id: uuid.UUID, session_id: uuid.UUID) -> None:
        self._db.execute(
            delete(RecipeEditLockModel).where(
                RecipeEditLockModel.recipe_id == recipe_id,
                RecipeEditLockModel.session_id == session_id,
            )
        )

    def recipe_lock_access(self, recipe_id: uuid.UUID, user_id: uuid.UUID) -> LockAccess | None:
        row = self._db.execute(
            select(NotebookModel.id, NotebookModel.kitchen_id)
            .join(RecipeModel, RecipeModel.notebook_id == NotebookModel.id)
            .where(RecipeModel.id == recipe_id)
        ).first()
        if row is None:
            return None
        notebook_id, kitchen_id = row
        if kitchen_id is not None:
            membership_id = self._db.scalar(
                select(KitchenMembershipModel.id)
                .join(KitchenModel, KitchenModel.id == KitchenMembershipModel.kitchen_id)
                .where(
                    KitchenMembershipModel.kitchen_id == kitchen_id,
                    KitchenMembershipModel.user_id == user_id,
                    KitchenModel.is_archived.is_(False),
                )
            )
            return None if membership_id is None else LockAccess(membership_id, None)
        member = self._db.scalar(
            select(NotebookMembershipModel.notebook_id).where(
                NotebookMembershipModel.notebook_id == notebook_id,
                NotebookMembershipModel.user_id == user_id,
            )
        )
        return None if member is None else LockAccess(None, notebook_id)

    def lock_recipe_row(self, recipe_id: uuid.UUID) -> bool:
        found = self._db.scalar(
            select(RecipeModel.id).where(RecipeModel.id == recipe_id).with_for_update()
        )
        return found is not None

    def release_all_for_kitchen(self, kitchen_id: uuid.UUID) -> None:
        self._db.execute(
            delete(CartEditLockModel).where(CartEditLockModel.cart_id == _cart_id(kitchen_id))
        )
        recipes = (
            select(RecipeModel.id)
            .join(NotebookModel, NotebookModel.id == RecipeModel.notebook_id)
            .where(NotebookModel.kitchen_id == kitchen_id)
        )
        self._db.execute(
            delete(RecipeEditLockModel).where(RecipeEditLockModel.recipe_id.in_(recipes))
        )
