"""
Modelo: price_history — datos OHLCV históricos por par y granularidad.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

PRICE_INTERVALS = ("1d", "1w", "1M")


class PriceHistory(Base):
    __tablename__ = "price_history"

    __table_args__ = (
        sa.UniqueConstraint("symbol", "interval", "open_at", name="uq_price_history_symbol_interval_open_at"),
        sa.Index("ix_price_history_symbol_interval_open_at", "symbol", "interval", "open_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    interval: Mapped[str] = mapped_column(
        sa.Enum(*PRICE_INTERVALS, name="price_interval"),
        nullable=False,
    )
    open_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    # NUMERIC(20,8) para precios en USD
    open: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(sa.NUMERIC(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(sa.NUMERIC(30, 8), nullable=False)
