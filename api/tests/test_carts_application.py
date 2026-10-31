"""Cart use cases and the cart edit lock against fake ports (spec 022)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from application.carts import (
    AddToDraftService,
    DiscardCartService,
    GetCartService,
    RemoveFromDraftService,
    ReplaceDraftService,
    SaveCartService,
    StartCartEditService,
)
from application.ports import (
    CartDraft,
    CartRecipeFacts,
    CartRepository,
    EditLockRepository,
    LockAccess,
    LockHolder,
    SavedCart,
    SessionRef,
)
from domain.cart import LOCK_IDLE
from domain.errors import (
    CartLockedError,
    CartValueError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotEditingError,
    RecipeNotFoundError,
)
from tests.test_notebooks_application import (
    World,
    _join,
    _kitchen,
    _kitchen_notebook,
    _personal,
    _world,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


@dataclass
class _Lock:
    session_id: UUID
    user_id: UUID
    last_active_at: datetime
    draft: CartDraft | None = None
    access: LockAccess | None = None


@dataclass
class Clock:
    now: datetime = NOW

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@dataclass
class FakeCartRepo:
    """Carts and recipes in memory, with the add counts and a log of saves."""

    world: World
    carts: dict[UUID, SavedCart] = field(default_factory=dict)
    recipes: dict[UUID, CartRecipeFacts] = field(default_factory=dict)
    counts: dict[UUID, int] = field(default_factory=dict)
    saves: list[UUID] = field(default_factory=list)
    for_update: list[UUID] = field(default_factory=list)

    def add_recipe(self, notebook_id: UUID, title: str = "Tomato rice", base: int = 4) -> UUID:
        notebook = self.world.notebooks.notebooks[notebook_id]
        recipe_id = uuid4()
        self.recipes[recipe_id] = CartRecipeFacts(
            recipe_id, title, notebook_id, notebook.name, base, notebook.kitchen_id
        )
        self.counts[recipe_id] = 0
        return recipe_id

    def delete_recipe(self, recipe_id: UUID) -> None:
        del self.recipes[recipe_id]
        for kitchen_id, cart in self.carts.items():
            self.carts[kitchen_id] = SavedCart(
                kitchen_id, tuple(i for i in cart.items if i.recipe_id != recipe_id)
            )

    def get_or_create_for_update(self, kitchen_id: UUID) -> SavedCart:
        self.for_update.append(kitchen_id)
        return self.carts.setdefault(kitchen_id, SavedCart(kitchen_id, ()))

    def read(self, kitchen_id: UUID) -> SavedCart:
        return self.carts.get(kitchen_id, SavedCart(kitchen_id, ()))

    def recipe_facts(self, recipe_ids: Sequence[UUID]) -> dict[UUID, CartRecipeFacts]:
        return {rid: self.recipes[rid] for rid in recipe_ids if rid in self.recipes}

    def save(self, kitchen_id: UUID, draft: CartDraft, user_id: UUID) -> tuple[UUID, ...]:
        before = {i.recipe_id for i in self.read(kitchen_id).items}
        added = tuple(i.recipe_id for i in draft.items if i.recipe_id not in before)
        for rid in added:
            self.counts[rid] += 1
        self.carts[kitchen_id] = SavedCart(kitchen_id, draft.items)
        self.saves.append(kitchen_id)
        return added


@dataclass
class FakeLocks:
    """Edit locks in memory. Liveness: session not in `dead_sessions`, holder still a member of
    a non-archived kitchen (cart) or not in `no_write` (recipe), and active within LOCK_IDLE."""

    world: World
    carts: FakeCartRepo
    clock: Clock = field(default_factory=Clock)
    cart_locks: dict[UUID, _Lock] = field(default_factory=dict)
    recipe_locks: dict[UUID, _Lock] = field(default_factory=dict)
    dead_sessions: set[UUID] = field(default_factory=set)
    no_write: set[tuple[UUID, UUID]] = field(default_factory=set)

    def now(self) -> datetime:
        return self.clock.now

    def _alive(self, lock: _Lock) -> bool:
        return (
            lock.session_id not in self.dead_sessions
            and self.clock.now - lock.last_active_at < LOCK_IDLE
        )

    def _holder(self, lock: _Lock | None) -> LockHolder | None:
        if lock is None:
            return None
        return LockHolder(
            lock.session_id,
            lock.user_id,
            self.world.notebooks.aliases.get(lock.user_id),
            lock.last_active_at,
        )

    def _live_cart(self, kitchen_id: UUID) -> _Lock | None:
        lock = self.cart_locks.get(kitchen_id)
        kitchen = self.world.kitchens.get_kitchen(kitchen_id)
        if lock is None or kitchen is None or kitchen.is_archived or not self._alive(lock):
            return None
        if self.world.kitchens.get_membership(kitchen_id, lock.user_id) is None:
            return None
        return lock

    def cart_holder(self, kitchen_id: UUID) -> LockHolder | None:
        return self._holder(self._live_cart(kitchen_id))

    def cart_draft(self, kitchen_id: UUID, session_id: UUID) -> CartDraft | None:
        lock = self._live_cart(kitchen_id)
        return lock.draft if lock is not None and lock.session_id == session_id else None

    def take_cart(
        self, kitchen_id: UUID, ref: SessionRef, membership_id: UUID, draft: CartDraft
    ) -> None:
        self.cart_locks[kitchen_id] = _Lock(ref.session_id, ref.user_id, self.clock.now, draft)

    def touch_cart(self, kitchen_id: UUID, session_id: UUID) -> None:
        lock = self.cart_locks.get(kitchen_id)
        if lock is not None and lock.session_id == session_id:
            lock.last_active_at = self.clock.now

    def set_cart_draft(self, kitchen_id: UUID, session_id: UUID, draft: CartDraft) -> None:
        lock = self.cart_locks.get(kitchen_id)
        if lock is not None and lock.session_id == session_id:
            lock.draft = draft
            lock.last_active_at = self.clock.now

    def kitchen_membership_id(self, kitchen_id: UUID, user_id: UUID) -> UUID | None:
        found = self.world.kitchens.get_membership(kitchen_id, user_id)
        return None if found is None else uuid4()

    def release_cart(self, kitchen_id: UUID, session_id: UUID) -> None:
        lock = self.cart_locks.get(kitchen_id)
        if lock is not None and lock.session_id == session_id:
            del self.cart_locks[kitchen_id]

    def recipe_holder(self, recipe_id: UUID) -> LockHolder | None:
        lock = self.recipe_locks.get(recipe_id)
        if lock is None or not self._alive(lock) or (recipe_id, lock.user_id) in self.no_write:
            return None
        return self._holder(lock)

    def take_recipe(self, recipe_id: UUID, ref: SessionRef, access: LockAccess) -> None:
        self.recipe_locks[recipe_id] = _Lock(
            ref.session_id, ref.user_id, self.clock.now, access=access
        )

    def touch_recipe(self, recipe_id: UUID, session_id: UUID) -> None:
        lock = self.recipe_locks.get(recipe_id)
        if lock is not None and lock.session_id == session_id:
            lock.last_active_at = self.clock.now

    def release_recipe(self, recipe_id: UUID, session_id: UUID) -> None:
        lock = self.recipe_locks.get(recipe_id)
        if lock is not None and lock.session_id == session_id:
            del self.recipe_locks[recipe_id]

    def recipe_lock_access(self, recipe_id: UUID, user_id: UUID) -> LockAccess | None:
        return None if (recipe_id, user_id) in self.no_write else LockAccess(uuid4(), None)

    def lock_recipe_row(self, recipe_id: UUID) -> bool:
        return True

    def release_all_for_kitchen(self, kitchen_id: UUID) -> None:
        self.cart_locks.pop(kitchen_id, None)
        for rid, facts in self.carts.recipes.items():
            if facts.kitchen_id == kitchen_id:
                self.recipe_locks.pop(rid, None)


ANA, BEN, CAT, DAN = uuid4(), uuid4(), uuid4(), uuid4()


class _NoList:
    def refresh(self, kitchen_id: UUID) -> None:
        pass


@dataclass
class Setup:
    world: World
    carts: FakeCartRepo
    locks: FakeLocks
    kitchen: UUID
    notebook: UUID
    ana: SessionRef
    ben: SessionRef

    def svc(self, cls):  # noqa: ANN001, ANN201
        if cls is SaveCartService:
            return cls(self.world.kitchens, self.carts, self.locks, _NoList())
        return cls(self.world.kitchens, self.carts, self.locks)

    def get(self, ref: SessionRef):  # noqa: ANN201
        return self.svc(GetCartService).execute(ref, self.kitchen)

    def add(self, ref: SessionRef, recipe_id: UUID):  # noqa: ANN201
        return self.svc(AddToDraftService).execute(ref, self.kitchen, recipe_id)

    def remove(self, ref: SessionRef, recipe_id: UUID):  # noqa: ANN201
        return self.svc(RemoveFromDraftService).execute(ref, self.kitchen, recipe_id)

    def put(self, ref: SessionRef, items: list[tuple[UUID, object]]):  # noqa: ANN201
        return self.svc(ReplaceDraftService).execute(ref, self.kitchen, items)

    def start(self, ref: SessionRef):  # noqa: ANN201
        return self.svc(StartCartEditService).execute(ref, self.kitchen)

    def save(self, ref: SessionRef):  # noqa: ANN201
        return self.svc(SaveCartService).execute(ref, self.kitchen)

    def discard(self, ref: SessionRef) -> None:
        self.svc(DiscardCartService).execute(ref, self.kitchen)


def _setup(*, archived: bool = False) -> Setup:
    world = _world({ANA: "ana", BEN: "ben", CAT: "cat", DAN: "dan"})
    kitchen = _kitchen(world, ANA, archived=archived)
    _join(world, kitchen, BEN)
    notebook = _kitchen_notebook(world, kitchen, "Ana's (Home) Notebook", ANA)
    carts = FakeCartRepo(world)
    return Setup(
        world=world,
        carts=carts,
        locks=FakeLocks(world, carts),
        kitchen=kitchen,
        notebook=notebook,
        ana=SessionRef(ANA, uuid4()),
        ben=SessionRef(BEN, uuid4()),
    )


def test_fakes_satisfy_the_ports() -> None:
    s = _setup()
    carts: CartRepository = s.carts
    locks: EditLockRepository = s.locks
    assert carts is not None and locks is not None


# --- US1: add, see, remove ------------------------------------------------------------------


def test_empty_cart_follows_the_member_count() -> None:
    s = _setup()
    view = s.get(s.ana)
    assert view.entries == ()
    assert view.entries == ()
    assert view.editor is None and view.draft is None and view.can_edit


def test_add_two_then_save_shows_both_and_frees_the_cart() -> None:
    s = _setup()
    a, b = s.carts.add_recipe(s.notebook, "A"), s.carts.add_recipe(s.notebook, "B")
    s.add(s.ana, a)
    view = s.add(s.ana, b)
    assert view.entries == ()  # the saved cart is unchanged until save
    assert view.draft is not None and [e.title for e in view.draft.entries] == ["A", "B"]
    result = s.save(s.ana)
    assert [(e.title, e.servings) for e in result.view.entries] == [("A", 4), ("B", 4)]
    assert result.view.editor is None
    assert s.locks.cart_locks == {}


def test_remove_then_save() -> None:
    s = _setup()
    a, b = s.carts.add_recipe(s.notebook), s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    s.add(s.ana, b)
    s.save(s.ana)
    s.remove(s.ana, a)
    assert [e.recipe_id for e in s.save(s.ana).view.entries] == [b]


def test_adding_twice_keeps_one_entry() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    view = s.add(s.ana, a)
    assert view.draft is not None and len(view.draft.entries) == 1


def test_personal_and_other_kitchen_recipes_cannot_be_added() -> None:
    s = _setup()
    personal = s.carts.add_recipe(_personal(s.world, ANA, "Mine"))
    other_kitchen = _kitchen(s.world, ANA, "Other")
    other = s.carts.add_recipe(_kitchen_notebook(s.world, other_kitchen, "Other nb", ANA))
    for recipe_id in (personal, other, uuid4()):
        with pytest.raises(RecipeNotFoundError):
            s.add(s.ana, recipe_id)


def test_non_member_and_unknown_kitchen_are_not_found() -> None:
    s = _setup()
    cat = SessionRef(CAT, uuid4())
    with pytest.raises(KitchenNotFoundError):
        s.get(cat)
    with pytest.raises(KitchenNotFoundError):
        s.svc(GetCartService).execute(s.ana, uuid4())
    with pytest.raises(KitchenNotFoundError):
        s.start(cat)


def test_discard_keeps_the_saved_cart_and_frees_it() -> None:
    s = _setup()
    a, b = s.carts.add_recipe(s.notebook), s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    s.save(s.ana)
    s.add(s.ana, b)
    s.discard(s.ana)
    s.discard(s.ana)  # idempotent
    view = s.get(s.ana)
    assert [e.recipe_id for e in view.entries] == [a] and view.editor is None


# --- US2: servings and factor ---------------------------------------------------------------


def test_add_starts_at_base_servings_and_factor_follows_servings() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook, base=4)
    s.add(s.ana, a)
    view = s.save(s.ana).view
    assert (view.entries[0].servings, view.entries[0].factor) == (4, "1")
    s.start(s.ana)
    view = s.put(s.ana, [(a, 6)])
    assert view.draft is not None and view.draft.entries[0].factor == "1.5"
    third = s.carts.add_recipe(s.notebook, base=3)
    s.put(s.ana, [(third, 2)])
    assert s.save(s.ana).view.entries[0].factor == "0.67"


def test_add_caps_a_base_above_the_servings_limit() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook, base=150)
    s.add(s.ana, a)
    assert s.save(s.ana).view.entries[0].servings == 99


@pytest.mark.parametrize("servings", [None, 0, 100, 1.5, "3", True])
def test_bad_numbers_are_refused_and_the_draft_is_unchanged(servings: object) -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook, base=4)
    s.add(s.ana, a)
    with pytest.raises(CartValueError) as info:
        s.put(s.ana, [(a, servings)])
    assert info.value.field == "servings"
    draft = s.get(s.ana).draft
    assert draft is not None and draft.entries[0].servings == 4


def test_duplicate_recipe_in_draft_is_refused() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook)
    s.start(s.ana)
    with pytest.raises(CartValueError) as info:
        s.put(s.ana, [(a, 1), (a, 2)])
    assert info.value.field == "items"


def test_factor_reads_the_recipe_base_servings_and_never_writes_it() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook, base=4)
    s.add(s.ana, a)
    s.save(s.ana)
    facts = s.carts.recipes[a]
    s.carts.recipes[a] = CartRecipeFacts(
        a, facts.title, facts.notebook_id, facts.notebook_name, 2, facts.kitchen_id
    )
    assert s.get(s.ana).entries[0].factor == "2"
    assert s.carts.recipes[a].base_servings == 2


# --- US3: one editor ------------------------------------------------------------------------


def test_other_member_sees_the_editor_and_is_refused() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook)
    s.start(s.ana)
    view = s.get(s.ben)
    assert view.editor is not None and view.editor.alias == "ana" and not view.editor.is_me
    assert view.editor.idle_expires_at is None
    assert not view.can_edit and view.draft is None
    for call in (
        lambda: s.start(s.ben),
        lambda: s.add(s.ben, a),
        lambda: s.remove(s.ben, a),
        lambda: s.put(s.ben, []),
        lambda: s.save(s.ben),
    ):
        with pytest.raises(CartLockedError) as info:
            call()
        assert info.value.editor_alias == "ana"


def test_save_and_put_without_any_editor_are_not_editing() -> None:
    s = _setup()
    with pytest.raises(NotEditingError):
        s.put(s.ben, [])
    with pytest.raises(NotEditingError):
        s.save(s.ben)


def test_save_frees_the_cart_for_others() -> None:
    s = _setup()
    s.start(s.ana)
    s.save(s.ana)
    assert s.start(s.ben).editor.is_me  # type: ignore[union-attr]


def test_dead_session_or_lost_membership_frees_the_cart_and_drops_the_draft() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    s.locks.dead_sessions.add(s.ana.session_id)
    view = s.start(s.ben)
    assert view.draft is not None and view.draft.entries == ()
    s.discard(s.ben)

    s.add(s.ben, a)
    s.world.kitchens.memberships = [m for m in s.world.kitchens.memberships if m.user_id != BEN]
    assert s.start(SessionRef(ANA, uuid4())).draft.entries == ()  # type: ignore[union-attr]


def test_same_session_keeps_its_draft_and_another_device_is_refused() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    view = s.start(s.ana)  # second tab, same session
    assert view.draft is not None and [e.recipe_id for e in view.draft.entries] == [a]
    with pytest.raises(CartLockedError):
        s.start(SessionRef(ANA, uuid4()))


def test_archived_kitchen_reads_but_refuses_edits() -> None:
    s = _setup(archived=True)
    view = s.get(s.ana)
    assert not view.can_edit
    with pytest.raises(KitchenArchivedError):
        s.start(s.ana)


def test_idle_limit_frees_the_cart_and_activity_renews_it() -> None:
    s = _setup()
    s.start(s.ana)
    s.locks.clock.advance(timedelta(minutes=4))
    s.put(s.ana, [])  # activity
    s.locks.clock.advance(timedelta(minutes=4))
    s.start(s.ana)  # keep-alive
    s.locks.clock.advance(timedelta(minutes=4, seconds=59))
    with pytest.raises(CartLockedError):
        s.start(s.ben)
    s.locks.clock.advance(timedelta(seconds=1))
    s.start(s.ben)
    with pytest.raises(CartLockedError):
        s.save(s.ana)
    s.discard(s.ben)
    with pytest.raises(NotEditingError):
        s.save(s.ana)


def test_my_lock_view_has_the_idle_expiry() -> None:
    s = _setup()
    view = s.start(s.ana)
    assert view.editor is not None and view.editor.idle_expires_at == NOW + LOCK_IDLE


# --- US5: consistency and add count ---------------------------------------------------------


def test_add_count_counts_saved_additions_only() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    s.save(s.ana)
    s.remove(s.ana, a)
    s.save(s.ana)
    s.add(s.ana, a)
    s.save(s.ana)
    assert s.carts.counts[a] == 2
    s.add(s.ana, a)  # already in the saved cart
    s.save(s.ana)
    b = s.carts.add_recipe(s.notebook)
    s.add(s.ana, b)
    s.discard(s.ana)
    assert s.carts.counts == {a: 2, b: 0}


def test_recipe_deleted_while_drafted_is_dropped_on_save() -> None:
    s = _setup()
    a, b = s.carts.add_recipe(s.notebook), s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    s.add(s.ana, b)
    s.carts.delete_recipe(a)
    draft = s.get(s.ana).draft
    assert draft is not None and [e.recipe_id for e in draft.entries] == [b]
    assert draft.dropped_recipe_ids == (a,)
    result = s.save(s.ana)
    assert result.dropped_recipe_ids == (a,)
    assert [e.recipe_id for e in result.view.entries] == [b]


def test_clear_then_save_empties_the_cart() -> None:
    s = _setup()
    a = s.carts.add_recipe(s.notebook)
    s.add(s.ana, a)
    s.save(s.ana)
    s.start(s.ana)
    s.put(s.ana, [])
    assert s.save(s.ana).view.entries == ()
