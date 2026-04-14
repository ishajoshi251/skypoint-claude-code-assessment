"""create users and candidate_profiles tables

Revision ID: 001
Revises:
Create Date: 2026-04-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (no-op if already exists)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Use raw SQL with IF NOT EXISTS so re-runs on a dirty volume don't crash
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            email       VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role        VARCHAR(10)  NOT NULL,
            is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")

    # Enum type — create only if absent
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE role AS ENUM ('HR', 'CANDIDATE');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # candidate_profiles (stub — full columns added in next migration)
    op.execute("""
        CREATE TABLE IF NOT EXISTS candidate_profiles (
            id      SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_candidate_profiles_id ON candidate_profiles (id)")


def downgrade() -> None:
    op.drop_table("candidate_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS role")
