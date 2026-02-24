"""create portfolio_snapshots table (caché de métricas calculadas)

Revision ID: 005_create_portfolio_snapshots
Revises: 004_create_price_history
Create Date: 2026-02-22 00:04:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "005_create_portfolio_snapshots"
down_revision: Union[str, None] = "004_create_price_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        # Una fila por cuenta por día
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        # NUMERIC(20,8): valores en USD
        sa.Column("total_value_usd", sa.NUMERIC(20, 8), nullable=False),
        sa.Column("invested_usd", sa.NUMERIC(20, 8), nullable=False),
        sa.Column("pnl_unrealized_usd", sa.NUMERIC(20, 8), nullable=False),
        sa.Column("pnl_realized_usd", sa.NUMERIC(20, 8), nullable=False),
        # NUMERIC(36,18): cantidad de BTC (precisión satoshi)
        sa.Column("btc_amount", sa.NUMERIC(36, 18), nullable=True),
        sa.Column("btc_avg_buy_price", sa.NUMERIC(20, 8), nullable=True),
        # composition_json: desglose por activo en esa fecha
        sa.Column("composition_json", JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Un único snapshot por cuenta por día
        sa.UniqueConstraint(
            "account_id",
            "snapshot_date",
            name="uq_portfolio_snapshots_account_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("portfolio_snapshots")
