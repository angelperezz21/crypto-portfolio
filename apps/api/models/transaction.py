"""
Modelo: transactions — historial de trades, depósitos, retiros y conversiones.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

TRANSACTION_TYPES = (
    "buy",
    "sell",
    "deposit",
    "withdrawal",
    "convert",
    "earn_interest",
    "staking_reward",
)


class Transaction(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        sa.Index("ix_transactions_account_executed", "account_id", "executed_at"),
        sa.Index("ix_transactions_asset_executed", "base_asset", "executed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False)
    binance_id: Mapped[str | None] = mapped_column(sa.String(100), unique=True, nullable=True)
    type: Mapped[str] = mapped_column(
        sa.Enum(*TRANSACTION_TYPES, name="transaction_type"),
        nullable=False,
    )
    base_asset: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    quote_asset: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    # NUNCA usar float: NUMERIC(36,18) para cantidades cripto
    quantity: Mapped[Decimal] = mapped_column(sa.NUMERIC(36, 18), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(36, 18), nullable=True)
    total_value_usd: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(20, 8), nullable=True)
    fee_asset: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    fee_amount: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(36, 18), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relaciones
    account: Mapped["Account"] = relationship(back_populates="transactions")  # noqa: F821
