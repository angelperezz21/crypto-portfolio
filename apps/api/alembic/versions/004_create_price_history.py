"""create price_history table (OHLCV)

Revision ID: 004_create_price_history
Revises: 003_create_balances_snapshot
Create Date: 2026-02-22 00:03:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision: str = "004_create_price_history"
down_revision: Union[str, None] = "003_create_balances_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRICE_INTERVALS = ("1d", "1w", "1M")

_price_interval = PgEnum(*PRICE_INTERVALS, name="price_interval", create_type=False)


def upgrade() -> None:
    # Crear el ENUM de forma idempotente
    values = ", ".join(f"'{v}'" for v in PRICE_INTERVALS)
    op.execute(
        f"DO $$ BEGIN "
        f"CREATE TYPE price_interval AS ENUM ({values}); "
        f"EXCEPTION WHEN duplicate_object THEN NULL; "
        f"END $$;"
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("interval", _price_interval, nullable=False),
        sa.Column("open_at", sa.TIMESTAMP(timezone=True), nullable=False),
        # NUMERIC(20,8): precios en USD con 8 decimales (estándar Binance)
        sa.Column("open", sa.NUMERIC(20, 8), nullable=False),
        sa.Column("high", sa.NUMERIC(20, 8), nullable=False),
        sa.Column("low", sa.NUMERIC(20, 8), nullable=False),
        sa.Column("close", sa.NUMERIC(20, 8), nullable=False),
        sa.Column("volume", sa.NUMERIC(30, 8), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # Constraint UNIQUE en (symbol, interval, open_at) para evitar duplicados en re-sync
        sa.UniqueConstraint(
            "symbol",
            "interval",
            "open_at",
            name="uq_price_history_symbol_interval_open_at",
        ),
    )

    # Índice compuesto para consultas por par y período
    op.create_index(
        "ix_price_history_symbol_interval_open_at",
        "price_history",
        ["symbol", "interval", "open_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_price_history_symbol_interval_open_at", table_name="price_history")
    op.drop_table("price_history")
    op.execute("DROP TYPE IF EXISTS price_interval;")
