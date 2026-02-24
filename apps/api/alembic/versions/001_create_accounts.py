"""create accounts table

Revision ID: 001_create_accounts
Revises:
Create Date: 2026-02-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision: str = "001_create_accounts"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PgEnum con create_type=False: el tipo se crea explícitamente vía op.execute()
# para garantizar idempotencia (DO block con EXCEPTION WHEN duplicate_object)
_sync_status = PgEnum("idle", "syncing", "error", name="sync_status", create_type=False)


def upgrade() -> None:
    # Crear el ENUM de forma idempotente — sin IF NOT EXISTS en PG para tipos
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE sync_status AS ENUM ('idle', 'syncing', 'error'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        # API Keys cifradas con AES-256-GCM — NUNCA en texto plano
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("api_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "sync_status",
            _sync_status,
            nullable=False,
            server_default="idle",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("accounts")
    op.execute("DROP TYPE IF EXISTS sync_status;")
