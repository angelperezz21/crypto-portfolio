"""
Modelo: portfolio_snapshots — caché de métricas calculadas por día.
"""

import uuid
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    __table_args__ = (
        sa.UniqueConstraint("account_id", "snapshot_date", name="uq_portfolio_snapshots_account_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    # NUMERIC(20,8) para valores en USD
    total_value_usd: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    invested_usd: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    pnl_unrealized_usd: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    pnl_realized_usd: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    # NUMERIC(36,18) para cantidad de BTC
    btc_amount: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(36, 18), nullable=True)
    btc_avg_buy_price: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(20, 8), nullable=True)
    composition_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relaciones
    account: Mapped["Account"] = relationship(back_populates="portfolio_snapshots")  # noqa: F821
