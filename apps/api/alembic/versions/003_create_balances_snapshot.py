"""create balances_snapshot table

Revision ID: 003_create_balances_snapshot
Revises: 002_create_transactions
Create Date: 2026-02-22 00:02:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_create_balances_snapshot"
down_revision: Union[str, None] = "002_create_transactions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "balances_snapshot",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        # NUMERIC(36,18): precisión máxima para cantidades cripto
        sa.Column("free", sa.NUMERIC(36, 18), nullable=False),
        sa.Column("locked", sa.NUMERIC(36, 18), nullable=False),
        sa.Column("snapshot_at", sa.TIMESTAMP(timezone=True), nullable=False),
        # NUMERIC(20,8): valoración en USD
        sa.Column("value_usd", sa.NUMERIC(20, 8), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Índice para consultas por cuenta y timestamp
    op.create_index(
        "ix_balances_snapshot_account_snapshot_at",
        "balances_snapshot",
        ["account_id", "snapshot_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_balances_snapshot_account_snapshot_at", table_name="balances_snapshot")
    op.drop_table("balances_snapshot")
