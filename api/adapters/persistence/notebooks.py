"""SQLAlchemy notebook repository and the user's default-notebook pointer (spec 055)."""

from __future__ import annotations

from uuid import UUID

from domain.errors import PrincipalNotFoundError
from domain.notebook import Notebook
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from adapters.persistence.models import NotebookModel, UserModel


def _notebook(row: NotebookModel) -> Notebook:
    return Notebook(id=row.id, kitchen_id=row.kitchen_id, user_id=row.user_id, name=row.name)


class SqlAlchemyNotebookRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, notebook_id: UUID) -> Notebook | None:
        row = self._session.get(NotebookModel, notebook_id)
        return _notebook(row) if row is not None else None

    def for_kitchen(self, kitchen_id: UUID) -> Notebook | None:
        row = self._session.scalar(
            select(NotebookModel).where(NotebookModel.kitchen_id == kitchen_id).limit(1)
        )
        return _notebook(row) if row is not None else None

    def for_member(self, user_id: UUID) -> Notebook | None:
        row = self._session.scalar(
            select(NotebookModel)
            .join(UserModel, UserModel.default_notebook_id == NotebookModel.id)
            .where(UserModel.id == user_id, NotebookModel.user_id == user_id)
            .limit(1)
        )
        return _notebook(row) if row is not None else None

    def create(self, notebook: Notebook) -> None:
        # unique(kitchen_id) arbitrates two first reads of the same kitchen's
        # notebook; the loser re-reads instead of failing the request.
        self._session.execute(
            insert(NotebookModel)
            .values(
                id=notebook.id,
                kitchen_id=notebook.kitchen_id,
                user_id=notebook.user_id,
                name=notebook.name,
            )
            .on_conflict_do_nothing(index_elements=[NotebookModel.kitchen_id])
        )


class SqlAlchemyUserDefaultNotebook:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_update(self, user_id: UUID) -> UUID | None:
        row = self._session.execute(
            select(UserModel.id, UserModel.default_notebook_id)
            .where(UserModel.id == user_id)
            .with_for_update()
        ).first()
        if row is None:
            raise PrincipalNotFoundError()
        return row.default_notebook_id

    def set(self, user_id: UUID, notebook_id: UUID) -> None:
        row = self._session.get(UserModel, user_id)
        if row is None:
            raise PrincipalNotFoundError()
        row.default_notebook_id = notebook_id
        self._session.flush()
