"""Dashboard reads: plain SQL aggregates, no stored totals, no paging (spec 055 R17)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from application.ports import (
    AdminIngredientRow,
    AdminRecipeRow,
    AdminUnitRow,
    AdminUserRow,
)
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from adapters.persistence.models import UnitModel, UserModel
from adapters.persistence.recipes import SqlAlchemyRecipeRepository

_INGREDIENTS = text(
    """
    SELECT names.name,
           COUNT(DISTINCT line.recipe_id) AS recipes,
           COUNT(DISTINCT recipe.author_id) AS people
    FROM (SELECT name FROM recipe_ingredient UNION SELECT name FROM ingredient) AS names
    LEFT JOIN recipe_ingredient AS line ON line.name = names.name
    LEFT JOIN recipe ON recipe.id = line.recipe_id
    GROUP BY names.name
    ORDER BY recipes DESC, names.name
    """
)

_RECIPES = text(
    """
    SELECT recipe.id,
           recipe.title,
           recipe.cart_add_count AS cart_adds,
           notebook.name AS notebook_name,
           CASE WHEN notebook.kitchen_id IS NULL THEN 'personal' ELSE 'kitchen' END
             AS notebook_kind,
           CASE
             WHEN notebook.kitchen_id IS NULL THEN
               (SELECT count(*) FROM notebook_membership AS member
                WHERE member.notebook_id = notebook.id)
             ELSE
               (SELECT count(*) FROM kitchen_memberships AS member
                WHERE member.kitchen_id = notebook.kitchen_id)
           END AS people_with_access,
           CASE
             WHEN notebook.kitchen_id IS NULL THEN
               (SELECT array_agg(users.alias ORDER BY users.alias NULLS LAST, users.id)
                FROM notebook_membership AS member
                JOIN users ON users.id = member.user_id
                WHERE member.notebook_id = notebook.id)
             ELSE
               (SELECT array_agg(users.alias ORDER BY users.alias NULLS LAST, users.id)
                FROM kitchen_memberships AS member
                JOIN users ON users.id = member.user_id
                WHERE member.kitchen_id = notebook.kitchen_id)
           END AS people_aliases
    FROM recipe
    JOIN notebook ON notebook.id = recipe.notebook_id
    ORDER BY cart_adds DESC, recipe.title, recipe.id
    """
)

_USERS = text(
    """
    SELECT users.id,
           users.alias,
           COALESCE(sessions.open_sessions, 0) AS open_sessions,
           sessions.newest_session_at,
           COALESCE(recipes.recipes_authored, 0) AS recipes_authored,
           recipes.latest_recipe_at,
           COALESCE(carts.carts_created, 0) AS carts_created,
           COALESCE(carts.carts_edited, 0) AS carts_edited,
           COALESCE(carts.carts_closed, 0) AS carts_closed,
           carts.latest_cart_action_at
    FROM users
    LEFT JOIN (
      SELECT user_id,
             count(*) FILTER (WHERE expires_at > now()) AS open_sessions,
             max(created_at) AS newest_session_at
      FROM sessions GROUP BY user_id
    ) AS sessions ON sessions.user_id = users.id
    LEFT JOIN (
      SELECT author_id,
             count(*) AS recipes_authored,
             max(created_at) AS latest_recipe_at
      FROM recipe WHERE author_id IS NOT NULL GROUP BY author_id
    ) AS recipes ON recipes.author_id = users.id
    LEFT JOIN (
      SELECT user_id,
             count(*) FILTER (WHERE action = 'created') AS carts_created,
             count(*) FILTER (WHERE action = 'edited') AS carts_edited,
             count(*) FILTER (WHERE action = 'closed') AS carts_closed,
             max(created_at) AS latest_cart_action_at
      FROM cart_activity GROUP BY user_id
    ) AS carts ON carts.user_id = users.id
    ORDER BY users.alias ASC NULLS LAST, users.id
    """
)


class SqlAlchemyAdminReports:
    def __init__(self, session: Session) -> None:
        self._session = session

    def is_admin(self, user_id: UUID) -> bool:
        return bool(self._session.scalar(select(UserModel.is_admin).where(UserModel.id == user_id)))

    def units(self) -> Sequence[AdminUnitRow]:
        rows = list(
            self._session.scalars(
                select(UnitModel).order_by(UnitModel.reference_count.desc(), UnitModel.name)
            )
        )
        ids = {uid for row in rows for uid in row.user_references}
        aliases: dict[UUID, str | None] = {}
        if ids:
            aliases = dict(
                self._session.execute(
                    select(UserModel.id, UserModel.alias).where(UserModel.id.in_(ids))
                )
                .tuples()
                .all()
            )
        return [
            AdminUnitRow(
                name=row.name,
                user_references=tuple(row.user_references),
                user_aliases=tuple(
                    sorted(
                        (aliases.get(uid) for uid in row.user_references),
                        key=lambda alias: (alias is None, alias or ""),
                    )
                ),
                reference_count=row.reference_count,
                is_default=row.is_default,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def ingredients(self) -> Sequence[AdminIngredientRow]:
        return [AdminIngredientRow(**row._mapping) for row in self._session.execute(_INGREDIENTS)]

    def recipes(self) -> Sequence[AdminRecipeRow]:
        return [
            AdminRecipeRow(**{**row._mapping, "people_aliases": tuple(row.people_aliases or ())})
            for row in self._session.execute(_RECIPES)
        ]

    def users(self) -> Sequence[AdminUserRow]:
        return [AdminUserRow(**row._mapping) for row in self._session.execute(_USERS)]

    def delete_recipe(self, recipe_id: UUID) -> None:
        # Lines, steps, source, cart entries, locks and search data leave with it (see
        # DeleteRecipeService for the cascade list).
        SqlAlchemyRecipeRepository(self._session).delete(recipe_id)
