"""FR-018: a table with a vector never stores a list of related ids beside it (spec 073, T057).

Reads the ORM metadata only, so it needs no database.
"""

from __future__ import annotations

from adapters.persistence.base import Base
from adapters.persistence.vector import Vector
from sqlalchemy import ARRAY


def test_no_vector_table_has_an_array_column() -> None:
    offenders = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        if any(isinstance(column.type, Vector) for column in table.columns)
        for column in table.columns
        if isinstance(column.type, ARRAY)
    ]
    assert offenders == []
