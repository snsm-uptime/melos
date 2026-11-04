"""Builders for the spec 019 Postgres tests: invented people, kitchens, notebooks and recipes.

Rows are added straight through the models, in the caller's session; nothing here commits.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from adapters.persistence.embeddings import SqlAlchemyRecipeEmbeddings
from adapters.persistence.models import (
    KitchenMembershipModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
    StepModel,
    UserModel,
)
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from tests.embedding_fakes import fake_vector

MODEL = "fake-embed"
DIM = 768


def user(db: Session, alias: str) -> UUID:
    user_id = uuid4()
    db.add(
        UserModel(
            id=user_id,
            email=f"{alias}-{user_id.hex[:8]}@example.com",
            alias=f"{alias[:20]}{user_id.hex[:6]}",
            password_hash="not-a-real-hash",
        )
    )
    db.flush()
    return user_id


def kitchen(db: Session, owner: UUID, *, archived: bool = False) -> UUID:
    kitchen_id = uuid4()
    db.add(KitchenModel(id=kitchen_id, name="Home", owner_id=owner, is_archived=archived))
    db.flush()
    db.add(KitchenMembershipModel(id=uuid4(), kitchen_id=kitchen_id, user_id=owner, role="owner"))
    db.flush()
    return kitchen_id


def join_kitchen(db: Session, kitchen_id: UUID, user_id: UUID) -> UUID:
    membership_id = uuid4()
    db.add(
        KitchenMembershipModel(
            id=membership_id, kitchen_id=kitchen_id, user_id=user_id, role="member"
        )
    )
    db.flush()
    return membership_id


def personal_notebook(db: Session, owner: UUID, name: str = "Notebook") -> UUID:
    notebook_id = uuid4()
    db.add(NotebookModel(id=notebook_id, name=name))
    db.flush()
    db.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=owner, role="owner"))
    db.flush()
    return notebook_id


def add_member(db: Session, notebook_id: UUID, user_id: UUID) -> None:
    db.add(NotebookMembershipModel(notebook_id=notebook_id, user_id=user_id, role="member"))
    db.flush()


def kitchen_notebook(db: Session, kitchen_id: UUID, owner: UUID | None = None) -> UUID:
    notebook_id = uuid4()
    db.add(
        NotebookModel(
            id=notebook_id, name="Kitchen notebook", kitchen_id=kitchen_id, owner_user_id=owner
        )
    )
    db.flush()
    return notebook_id


def recipe(
    db: Session,
    notebook_id: UUID,
    title: str,
    ingredients: Sequence[str] = ("rice",),
    *,
    author_id: UUID | None = None,
    created_at: datetime | None = None,
    steps: Sequence[str] = ("Cook.",),
) -> UUID:
    recipe_id = uuid4()
    values = {"created_at": created_at} if created_at is not None else {}
    db.add(
        RecipeModel(
            id=recipe_id,
            notebook_id=notebook_id,
            author_id=author_id,
            title=title,
            base_servings=2,
            **values,
        )
    )
    db.flush()
    for position, name in enumerate(ingredients):
        db.add(
            RecipeIngredientModel(
                recipe_id=recipe_id, position=position, name=name, quantity=1, unit="unit"
            )
        )
    for position, step in enumerate(steps):
        db.add(StepModel(recipe_id=recipe_id, position=position, text=step))
    db.flush()
    return recipe_id


def version(db: Session, recipe_id: UUID) -> datetime:
    return db.scalar(select(RecipeModel.updated_at).where(RecipeModel.id == recipe_id))


def embed(
    db: Session,
    recipe_id: UUID,
    vector_text: str | None = None,
    *,
    model: str = MODEL,
    strategy: str = "toon",
) -> bool:
    """Write a current embedding of the recipe, from a fake vector of its title by default."""
    title = db.scalar(select(RecipeModel.title).where(RecipeModel.id == recipe_id))
    return SqlAlchemyRecipeEmbeddings(db).write_if_current(
        recipe_id,
        version(db, recipe_id),
        model,
        fake_vector(vector_text or title, DIM),
        strategy,
        12,
    )


def bump(db: Session, recipe_id: UUID) -> None:
    """Change the recipe's version, as an edit does."""
    db.execute(
        text("UPDATE recipe SET updated_at = clock_timestamp() WHERE id = :id"), {"id": recipe_id}
    )
    db.flush()


def age_jobs(db: Session, recipe_ids: Sequence[UUID]) -> None:
    """Make the jobs the oldest due ones, so a claim takes them before any other test's."""
    db.execute(
        text(
            "UPDATE embedding_job SET due_at = timestamptz '2000-01-01', "
            "enqueued_at = timestamptz '2000-01-01' WHERE recipe_id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": list(recipe_ids)},
    )


def job(db: Session, recipe_id: UUID):  # noqa: ANN201
    return db.execute(
        text("SELECT * FROM embedding_job WHERE recipe_id = :id"), {"id": recipe_id}
    ).first()


def embedding_row(db: Session, recipe_id: UUID, model: str = MODEL):  # noqa: ANN201
    return db.execute(
        text("SELECT * FROM recipe_embedding WHERE recipe_id = :id AND model = :model"),
        {"id": recipe_id, "model": model},
    ).first()
