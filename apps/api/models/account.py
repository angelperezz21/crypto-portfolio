"""
Modelo: accounts — credenciales de Binance y estado de sincronización.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    api_secret_encrypted: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(
        sa.Enum("idle", "syncing", "error", name="sync_status"),
        nullable=False,
        server_default="idle",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    # Relaciones
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")  # noqa: F821
    balance_snapshots: Mapped[list["BalanceSnapshot"]] = relationship(back_populates="account")  # noqa: F821
    portfolio_snapshots: Mapped[list["PortfolioSnapshot"]] = relationship(back_populates="account")  # noqa: F821
