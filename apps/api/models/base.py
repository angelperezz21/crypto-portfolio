"""
Base declarativa de SQLAlchemy. Todos los modelos heredan de aquí.
"""

import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Añade created_at con valor por defecto al momento de inserción."""

    created_at: Mapped[str] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()
