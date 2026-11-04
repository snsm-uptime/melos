"""A pgvector `vector(dim)` column without the pgvector package (spec 019 research R9).

Values are bound as pgvector's text form "[v1,v2,…]" and read back as a tuple of floats. The
extension itself comes from migration 0002.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from sqlalchemy.types import UserDefinedType


def to_vector_text(values: Sequence[float], dim: int | None = None) -> str:
    """pgvector's text form of the values; ValueError on a wrong length."""
    if dim is not None and len(values) != dim:
        raise ValueError(f"vector needs {dim} values, got {len(values)}")
    return "[" + ",".join(repr(float(value)) for value in values) + "]"


def from_vector_text(text: str) -> tuple[float, ...]:
    body = text.strip().removeprefix("[").removesuffix("]")
    if not body:
        return ()
    return tuple(float(part) for part in body.split(","))


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **_: Any) -> str:
        return f"vector({self.dim})"

    def bind_processor(self, dialect: Any) -> Callable[[Any], str | None]:
        dim = self.dim

        def process(value: Any) -> str | None:
            if value is None:
                return None
            return to_vector_text(value, dim)

        return process

    def result_processor(self, dialect: Any, coltype: Any) -> Callable[[Any], Any]:
        def process(value: Any) -> tuple[float, ...] | None:
            if value is None:
                return None
            return from_vector_text(value)

        return process
