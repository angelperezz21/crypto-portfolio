"""
Modelo: balances_snapshot — snapshot periódico de balances por activo.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class BalanceSnapshot(Base):
    __tablename__ = "balances_snapshot"

    __table_args__ = (
        sa.Index("ix_balances_snapshot_account_snapshot_at", "account_id", "snapshot_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False)
    asset: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    # NUMERIC(36,18) para cantidades cripto
    free: Mapped[Decimal] = mapped_column(sa.NUMERIC(36, 18), nullable=False)
    locked: Mapped[Decimal] = mapped_column(sa.NUMERIC(36, 18), nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    # NUMERIC(20,8) para precios/valores en USD
    value_usd: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(20, 8), nullable=True)

    # Relaciones
    account: Mapped["Account"] = relationship(back_populates="balance_snapshots")  # noqa: F821
