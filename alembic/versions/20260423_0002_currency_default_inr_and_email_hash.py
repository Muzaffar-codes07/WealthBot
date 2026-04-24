"""Align users.currency + transactions.currency defaults to INR; backfill email_hash.

Closes the CLAUDE.md-documented "USD vs INR default" gotcha by making the
DB-level server_default match the Pydantic schema default. Also backfills
the email_hash column (added as nullable in 0001) so /auth/refresh-style
lookups by hash are possible for all existing rows.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-23 00:00:00.000000+00:00
"""

from __future__ import annotations

import hashlib
import os
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "currency", server_default="INR")
    op.alter_column("transactions", "currency", server_default="INR")

    op.execute("UPDATE users SET currency = 'INR' WHERE currency = 'USD'")
    op.execute("UPDATE transactions SET currency = 'INR' WHERE currency = 'USD'")

    secret = os.environ.get("SECRET_KEY", "")
    if secret:
        bind = op.get_bind()
        rows = bind.execute(
            sa.text("SELECT id, email FROM users WHERE email_hash IS NULL")
        ).fetchall()
        for row in rows:
            digest = hashlib.sha256(f"{secret}{row.email.lower()}".encode()).hexdigest()
            bind.execute(
                sa.text("UPDATE users SET email_hash = :h WHERE id = :id"),
                {"h": digest, "id": row.id},
            )


def downgrade() -> None:
    op.alter_column("users", "currency", server_default=None)
    op.alter_column("transactions", "currency", server_default=None)
