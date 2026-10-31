"""The kitchen cart and its single editor (spec 022).

Every write goes through the cart edit lock and its draft (research R6, R7): the first write
takes the lock for the caller's session, the draft starts as a copy of the saved cart, and only
Save changes what other members see. Non-members and unknown kitchens get KitchenNotFoundError
(404); an archived kitchen reads but refuses writes.

Nothing is logged but outcomes and counts (constitution §4).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from domain.cart import SERVINGS_MAX, check_count, format_factor, idle_expires_at, scale_factor
from domain.errors import (
    CartLockedError,
    CartValueError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotEditingError,
    RecipeNotFoundError,
)

from application.kitchens import KitchenRepository
from application.ports import (
    CartDraft,
    CartDraftItem,
    CartRecipeFacts,
    CartRepository,
    EditLockRepository,
    LockHolder,
    SavedCart,
    SessionRef,
    ShoppingListRefresher,
)

logger = logging.getLogger(__name__)

MAX_ITEMS = 200


@dataclass(frozen=True, slots=True)
class EditorView:
    alias: str | None
    is_me: bool
    # Only for my own lock: when it ends without activity.
    idle_expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CartEntryView:
    recipe_id: UUID
    title: str
    notebook_id: UUID
    notebook_name: str
    base_servings: int
    servings: int
    factor: str


@dataclass(frozen=True, slots=True)
class CartDraftView:
    entries: tuple[CartEntryView, ...]
    # Drafted recipes that were deleted since.
    dropped_recipe_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class CartView:
    kitchen_id: UUID
    entries: tuple[CartEntryView, ...]
    editor: EditorView | None
    draft: CartDraftView | None
    can_edit: bool


@dataclass(frozen=True, slots=True)
class SavedCartResult:
    view: CartView
    dropped_recipe_ids: tuple[UUID, ...]


def editor_view(holder: LockHolder | None, ref: SessionRef | None) -> EditorView | None:
    if holder is None:
        return None
    is_me = ref is not None and holder.session_id == ref.session_id
    return EditorView(
        alias=holder.alias,
        is_me=is_me,
        idle_expires_at=idle_expires_at(holder.last_active_at) if is_me else None,
    )


def _entries(
    items: Sequence[CartDraftItem],
    facts: dict[UUID, CartRecipeFacts],
    kitchen_id: UUID,
) -> tuple[tuple[CartEntryView, ...], tuple[UUID, ...]]:
    entries: list[CartEntryView] = []
    dropped: list[UUID] = []
    for item in items:
        fact = facts.get(item.recipe_id)
        if fact is None or fact.kitchen_id != kitchen_id:
            dropped.append(item.recipe_id)
            continue
        entries.append(
            CartEntryView(
                recipe_id=fact.recipe_id,
                title=fact.title,
                notebook_id=fact.notebook_id,
                notebook_name=fact.notebook_name,
                base_servings=fact.base_servings,
                servings=item.servings,
                factor=format_factor(scale_factor(item.servings, fact.base_servings)),
            )
        )
    return tuple(entries), tuple(dropped)


class _CartUseCase:
    def __init__(
        self, kitchens: KitchenRepository, carts: CartRepository, locks: EditLockRepository
    ) -> None:
        self._kitchens = kitchens
        self._carts = carts
        self._locks = locks

    def _kitchen_is_archived(self, actor: UUID, kitchen_id: UUID) -> bool:
        kitchen = self._kitchens.get_kitchen(kitchen_id)
        if kitchen is None or self._kitchens.get_membership(kitchen_id, actor) is None:
            raise KitchenNotFoundError()
        return kitchen.is_archived

    def _writable(self, ref: SessionRef, kitchen_id: UUID) -> SavedCart:
        """Access, archive check, then the cart row lock that serializes writers (R5)."""
        if self._kitchen_is_archived(ref.user_id, kitchen_id):
            raise KitchenArchivedError()
        return self._carts.get_or_create_for_update(kitchen_id)

    def _my_draft(self, ref: SessionRef, kitchen_id: UUID) -> CartDraft:
        """The caller's draft; refused when someone else edits or nobody does."""
        holder = self._locks.cart_holder(kitchen_id)
        if holder is None:
            raise NotEditingError()
        if holder.session_id != ref.session_id:
            raise CartLockedError(holder.alias)
        draft = self._locks.cart_draft(kitchen_id, ref.session_id)
        if draft is None:
            raise NotEditingError()
        return draft

    def _start(self, ref: SessionRef, kitchen_id: UUID, saved: SavedCart) -> CartDraft:
        """Take the lock, or for the holder keep it alive; returns the caller's draft."""
        holder = self._locks.cart_holder(kitchen_id)
        if holder is not None and holder.session_id != ref.session_id:
            raise CartLockedError(holder.alias)
        if holder is not None:
            draft = self._locks.cart_draft(kitchen_id, ref.session_id)
            if draft is not None:
                self._locks.touch_cart(kitchen_id, ref.session_id)
                return draft
        membership_id = self._locks.kitchen_membership_id(kitchen_id, ref.user_id)
        if membership_id is None:
            raise KitchenNotFoundError()
        draft = CartDraft(items=saved.items)
        self._locks.take_cart(kitchen_id, ref, membership_id, draft)
        logger.info("cart edit outcome=locked items=%d", len(draft.items))
        return draft

    def _kitchen_recipe(self, kitchen_id: UUID, recipe_id: UUID) -> CartRecipeFacts:
        fact = self._carts.recipe_facts([recipe_id]).get(recipe_id)
        if fact is None or fact.kitchen_id != kitchen_id:
            raise RecipeNotFoundError()
        return fact

    def _view(self, ref: SessionRef, kitchen_id: UUID) -> CartView:
        archived = self._kitchen_is_archived(ref.user_id, kitchen_id)
        saved = self._carts.read(kitchen_id)
        holder = self._locks.cart_holder(kitchen_id)
        editor = editor_view(holder, ref)
        draft = (
            self._locks.cart_draft(kitchen_id, ref.session_id)
            if editor is not None and editor.is_me
            else None
        )
        ids = [i.recipe_id for i in saved.items] + (
            [i.recipe_id for i in draft.items] if draft else []
        )
        facts = self._carts.recipe_facts(list(dict.fromkeys(ids)))
        entries, _ = _entries(saved.items, facts, kitchen_id)
        draft_view = None
        if draft is not None:
            draft_entries, dropped = _entries(draft.items, facts, kitchen_id)
            draft_view = CartDraftView(entries=draft_entries, dropped_recipe_ids=dropped)
        return CartView(
            kitchen_id=kitchen_id,
            entries=entries,
            editor=editor,
            draft=draft_view,
            can_edit=not archived and (editor is None or editor.is_me),
        )


class GetCartService(_CartUseCase):
    def execute(self, ref: SessionRef, kitchen_id: UUID) -> CartView:
        return self._view(ref, kitchen_id)


class StartCartEditService(_CartUseCase):
    """Take the cart lock, or keep it alive for its holder (research R10)."""

    def execute(self, ref: SessionRef, kitchen_id: UUID) -> CartView:
        saved = self._writable(ref, kitchen_id)
        self._start(ref, kitchen_id, saved)
        return self._view(ref, kitchen_id)


class AddToDraftService(_CartUseCase):
    """Quick add from a card or the recipe page: starts at the recipe's servings (FR-015).

    A no-op when already drafted (R7).
    """

    def execute(self, ref: SessionRef, kitchen_id: UUID, recipe_id: UUID) -> CartView:
        saved = self._writable(ref, kitchen_id)
        fact = self._kitchen_recipe(kitchen_id, recipe_id)
        draft = self._start(ref, kitchen_id, saved)
        if all(i.recipe_id != recipe_id for i in draft.items):
            if len(draft.items) >= MAX_ITEMS:
                raise CartValueError("items")
            servings = min(fact.base_servings, SERVINGS_MAX)
            draft = replace(draft, items=(*draft.items, CartDraftItem(recipe_id, servings)))
        self._locks.set_cart_draft(kitchen_id, ref.session_id, draft)
        return self._view(ref, kitchen_id)


class RemoveFromDraftService(_CartUseCase):
    def execute(self, ref: SessionRef, kitchen_id: UUID, recipe_id: UUID) -> CartView:
        saved = self._writable(ref, kitchen_id)
        draft = self._start(ref, kitchen_id, saved)
        draft = replace(draft, items=tuple(i for i in draft.items if i.recipe_id != recipe_id))
        self._locks.set_cart_draft(kitchen_id, ref.session_id, draft)
        return self._view(ref, kitchen_id)


class ReplaceDraftService(_CartUseCase):
    """The ui sends the whole draft on each change (research R6). Holder only."""

    def execute(
        self,
        ref: SessionRef,
        kitchen_id: UUID,
        items: Sequence[tuple[UUID, object]],
    ) -> CartView:
        self._writable(ref, kitchen_id)
        self._my_draft(ref, kitchen_id)
        if len(items) > MAX_ITEMS:
            raise CartValueError("items")
        checked = tuple(
            CartDraftItem(rid, check_count(servings, "servings")) for rid, servings in items
        )
        ids = [i.recipe_id for i in checked]
        if len(set(ids)) != len(ids):
            raise CartValueError("items")
        facts = self._carts.recipe_facts(ids)
        if any(rid not in facts or facts[rid].kitchen_id != kitchen_id for rid in ids):
            raise RecipeNotFoundError()
        self._locks.set_cart_draft(kitchen_id, ref.session_id, CartDraft(checked))
        return self._view(ref, kitchen_id)


class SaveCartService(_CartUseCase):
    """Apply the draft, raise the add count of newly added recipes, free the cart (R6, R8).

    The active shopping list follows in the same transaction (spec 025 FR-001).
    """

    def __init__(
        self,
        kitchens: KitchenRepository,
        carts: CartRepository,
        locks: EditLockRepository,
        shopping_list: ShoppingListRefresher,
    ) -> None:
        super().__init__(kitchens, carts, locks)
        self._shopping_list = shopping_list

    def execute(self, ref: SessionRef, kitchen_id: UUID) -> SavedCartResult:
        self._writable(ref, kitchen_id)
        draft = self._my_draft(ref, kitchen_id)
        facts = self._carts.recipe_facts([i.recipe_id for i in draft.items])
        kept = tuple(
            i
            for i in draft.items
            if i.recipe_id in facts and facts[i.recipe_id].kitchen_id == kitchen_id
        )
        dropped = tuple(i.recipe_id for i in draft.items if i not in kept)
        added = self._carts.save(kitchen_id, CartDraft(kept), ref.user_id)
        self._shopping_list.refresh(kitchen_id)
        self._locks.release_cart(kitchen_id, ref.session_id)
        logger.info(
            "cart save outcome=saved items=%d added=%d dropped=%d",
            len(kept),
            len(added),
            len(dropped),
        )
        return SavedCartResult(view=self._view(ref, kitchen_id), dropped_recipe_ids=dropped)


class DiscardCartService(_CartUseCase):
    """Drop the caller's draft and free the cart. Idempotent."""

    def execute(self, ref: SessionRef, kitchen_id: UUID) -> None:
        self._kitchen_is_archived(ref.user_id, kitchen_id)
        self._locks.release_cart(kitchen_id, ref.session_id)
        logger.info("cart edit outcome=discarded")


@dataclass(frozen=True, slots=True)
class RecipeCartStatus:
    in_cart: bool
    editor: EditorView | None


def recipe_cart_status(
    carts: CartRepository,
    locks: EditLockRepository,
    kitchen_id: UUID,
    recipe_id: UUID,
    ref: SessionRef | None,
) -> RecipeCartStatus:
    """Whether a kitchen recipe is in the cart as the caller sees it: my draft while I edit,
    else the saved cart. The caller has already checked access to the recipe."""
    holder = locks.cart_holder(kitchen_id)
    editor = editor_view(holder, ref)
    items: Sequence[CartDraftItem] = carts.read(kitchen_id).items
    if editor is not None and editor.is_me and ref is not None:
        draft = locks.cart_draft(kitchen_id, ref.session_id)
        if draft is not None:
            items = draft.items
    return RecipeCartStatus(in_cart=any(i.recipe_id == recipe_id for i in items), editor=editor)
