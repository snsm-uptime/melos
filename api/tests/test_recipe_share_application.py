"""Sharing one recipe with a co-member against fake ports (spec 071).

The co-member ordering rule itself lives in one SQL query and is tested on Postgres in
test_recipe_share_integration.py. Here the list service is checked to keep that order.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from application.ports import CoMemberRecord, RecipeDetail, RecipeLineDetail
from application.recipe_share import (
    ListShareCandidatesService,
    ShareRecipeCommand,
    ShareRecipeService,
)
from domain.errors import (
    AliasRequiredError,
    RecipeNotFoundError,
    ShareRecipientNotFoundError,
    ShareSelfError,
)
from tests.embedding_fakes import FakeEmbeddingJobs
from tests.test_notebooks_application import World, _personal, _world

ANA, BEN, CAM = uuid4(), uuid4(), uuid4()
NOW = datetime(2026, 11, 5, tzinfo=UTC)


def _line(name: str) -> RecipeLineDetail:
    return RecipeLineDetail(
        name=name, vague=False, quantity=1, unit="cup", size=None, preparation=None, note=None
    )


@dataclass
class FakeRecipes:
    details: dict[UUID, RecipeDetail] = field(default_factory=dict)
    # copy id -> (source id, notebook id, author id, link_source)
    copies: dict[UUID, tuple[UUID, UUID, UUID, bool]] = field(default_factory=dict)
    renames: dict[UUID, dict[str, str]] = field(default_factory=dict)

    def add(self, notebook_id: UUID, *names: str) -> UUID:
        recipe_id = uuid4()
        self.details[recipe_id] = RecipeDetail(
            id=recipe_id,
            notebook_id=notebook_id,
            title="Lentil soup",
            base_servings=4,
            servings_estimated=False,
            author_alias="ana",
            lines=tuple(_line(n) for n in names),
            steps=("Cook.",),
            source_type="text",
            source_url=None,
            created_at=NOW,
            updated_at=NOW,
        )
        return recipe_id

    def get_detail(self, recipe_id: UUID) -> RecipeDetail | None:
        return self.details.get(recipe_id)

    def copy_one(
        self, source: UUID, target: UUID, author: UUID, *, link_source: bool = True
    ) -> UUID | None:
        if source not in self.details:
            return None
        copy_id = uuid4()
        self.copies[copy_id] = (source, target, author, link_source)
        return copy_id

    def rename_line_names(self, recipe_id: UUID, renames: Mapping[str, str]) -> None:
        self.renames[recipe_id] = dict(renames)


@dataclass
class FakeDirectory:
    """Co-members per user, already in the order the SQL adapter returns."""

    peers: dict[UUID, list[CoMemberRecord]] = field(default_factory=dict)

    def list_co_members(self, user_id: UUID) -> list[CoMemberRecord]:
        return list(self.peers.get(user_id, []))

    def is_co_member(self, user_id: UUID, other_id: UUID) -> bool:
        return any(p.user_id == other_id for p in self.peers.get(user_id, []))


def _peer(user_id: UUID, alias: str, shared_at: datetime | None = NOW) -> CoMemberRecord:
    return CoMemberRecord(user_id=user_id, alias=alias, shared_at=shared_at)


@pytest.fixture
def world() -> World:
    return _world({ANA: "ana", BEN: "ben", CAM: "cam"})


@pytest.fixture
def recipes() -> FakeRecipes:
    return FakeRecipes()


@pytest.fixture
def directory() -> FakeDirectory:
    return FakeDirectory({ANA: [_peer(BEN, "ben")], BEN: [_peer(ANA, "ana")]})


def _share(
    world: World,
    recipes: FakeRecipes,
    directory: FakeDirectory,
    source: UUID,
    *,
    actor: UUID = ANA,
    recipient: UUID = BEN,
    jobs: FakeEmbeddingJobs | None = None,
):
    service = ShareRecipeService(
        recipes,
        world.notebooks,
        world.catalog,
        world.prefs,
        directory,
        world.defaults,
        embedding_jobs=jobs,
    )
    return service.execute(
        ShareRecipeCommand(actor_id=actor, recipe_id=source, recipient_id=recipient)
    )


# --- T010: candidates -------------------------------------------------------------------------


def test_candidates_keep_the_directory_order(directory: FakeDirectory) -> None:
    older = datetime(2026, 1, 1, tzinfo=UTC)
    directory.peers[ANA] = [
        _peer(CAM, "cam"),
        _peer(BEN, "ben", older),
        _peer(uuid4(), "dee", None),
    ]
    listed = ListShareCandidatesService(directory).execute(ANA)
    assert [p.alias for p in listed] == ["cam", "ben", "dee"]


def test_candidates_are_empty_for_a_person_who_shares_nothing() -> None:
    assert ListShareCandidatesService(FakeDirectory()).execute(ANA) == []


# --- T012: share ------------------------------------------------------------------------------


def test_copy_lands_in_the_recipients_default_notebook_as_theirs(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "lentils", "onion", "lentils")
    bens_default = _personal(world, BEN, "ben's Notebook")
    world.notebooks.defaults[BEN] = bens_default
    jobs = FakeEmbeddingJobs()

    shared = _share(world, recipes, directory, source, jobs=jobs)

    assert shared.notebook_id == bens_default
    assert shared.recipient_alias == "ben"
    # No link back to the source (FR-011).
    assert recipes.copies[shared.recipe_id] == (source, bens_default, BEN, False)
    assert {"lentils", "onion"} <= world.catalog.names[bens_default]
    assert jobs.enqueued == [shared.recipe_id]


def test_source_recipe_is_unchanged(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "tomatoes")
    before = recipes.details[source]
    world.notebooks.defaults[BEN] = _personal(world, BEN, "ben's Notebook", {"tomato"})

    shared = _share(world, recipes, directory, source)

    assert recipes.details[source] == before
    assert source not in recipes.renames
    assert shared.recipe_id != source


def test_names_take_the_recipients_catalog_spelling(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "tomatoes", "basil")
    bens_default = _personal(world, BEN, "ben's Notebook", {"tomato"})
    world.notebooks.defaults[BEN] = bens_default

    shared = _share(world, recipes, directory, source)

    assert recipes.renames[shared.recipe_id] == {"tomatoes": "tomato"}
    assert world.catalog.names[bens_default] == {"tomato", "basil"}


def test_a_recipient_without_a_default_notebook_gets_one(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")

    shared = _share(world, recipes, directory, source)

    assert world.notebooks.defaults[BEN] == shared.notebook_id
    assert world.notebooks.notebooks[shared.notebook_id].kitchen_id is None


def test_a_recipient_who_is_not_a_co_member_is_not_found(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    with pytest.raises(ShareRecipientNotFoundError):
        _share(world, recipes, directory, source, recipient=CAM)
    with pytest.raises(ShareRecipientNotFoundError):
        _share(world, recipes, directory, source, recipient=uuid4())
    assert recipes.copies == {}


def test_sharing_with_yourself_is_refused(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    with pytest.raises(ShareSelfError):
        _share(world, recipes, directory, source, recipient=ANA)
    assert recipes.copies == {}


def test_an_unreadable_or_missing_recipe_is_not_found(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    cams = recipes.add(_personal(world, CAM, "cam's Notebook"), "rice")
    with pytest.raises(RecipeNotFoundError):
        _share(world, recipes, directory, cams)
    with pytest.raises(RecipeNotFoundError):
        _share(world, recipes, directory, uuid4())
    assert recipes.copies == {}


def test_a_recipient_with_no_alias_gets_no_notebook_and_no_copy(
    world: World, recipes: FakeRecipes, directory: FakeDirectory
) -> None:
    # Without an alias no default notebook can be named, so nothing is written.
    del world.prefs.aliases[BEN]
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    with pytest.raises(AliasRequiredError):
        _share(world, recipes, directory, source)
    assert recipes.copies == {}
    assert BEN not in world.notebooks.defaults
