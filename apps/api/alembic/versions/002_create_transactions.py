"""create transactions table

Revision ID: 002_create_transactions
Revises: 001_create_accounts
Create Date: 2026-02-22 00:01:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum, JSONB

revision: str = "002_create_transactions"
down_revision: Union[str, None] = "001_create_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TRANSACTION_TYPES = (
    "buy",
    "sell",
    "deposit",
    "withdrawal",
    "convert",
    "earn_interest",
    "staking_reward",
)

_transaction_type = PgEnum(*TRANSACTION_TYPES, name="transaction_type", create_type=False)


def upgrade() -> None:
    # Crear el ENUM de forma idempotente
    values = ", ".join(f"'{v}'" for v in TRANSACTION_TYPES)
    op.execute(
        f"DO $$ BEGIN "
        f"CREATE TYPE transaction_type AS ENUM ({values}); "
        f"EXCEPTION WHEN duplicate_object THEN NULL; "
        f"END $$;"
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        # binance_id: ID original de Binance — UNIQUE para evitar duplicados en re-sync
        sa.Column("binance_id", sa.String(100), nullable=True),
        sa.Column("type", _transaction_type, nullable=False),
        sa.Column("base_asset", sa.String(20), nullable=False),
        sa.Column("quote_asset", sa.String(20), nullable=True),
        # NUMERIC(36,18): precisión máxima para cantidades cripto (estándar ERC-20)
        sa.Column("quantity", sa.NUMERIC(36, 18), nullable=False),
        sa.Column("price", sa.NUMERIC(36, 18), nullable=True),
        # NUMERIC(20,8): precios/valores en USD
        sa.Column("total_value_usd", sa.NUMERIC(20, 8), nullable=True),
        sa.Column("fee_asset", sa.String(20), nullable=True),
        sa.Column("fee_amount", sa.NUMERIC(36, 18), nullable=True),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        # raw_data: payload original de Binance para trazabilidad
        sa.Column("raw_data", JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("binance_id"),
    )

    # Índices según db-patterns skill
    op.create_index(
        "ix_transactions_account_executed",
        "transactions",
        ["account_id", "executed_at"],
    )
    op.create_index(
        "ix_transactions_asset_executed",
        "transactions",
        ["base_asset", "executed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_asset_executed", table_name="transactions")
    op.drop_index("ix_transactions_account_executed", table_name="transactions")
    op.drop_table("transactions")
    op.execute("DROP TYPE IF EXISTS transaction_type;")
