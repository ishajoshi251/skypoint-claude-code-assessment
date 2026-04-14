"""005 create invites table

Revision ID: 005
Revises: 004
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invitestatus') THEN
                CREATE TYPE invitestatus AS ENUM ('PENDING', 'SENT', 'ACCEPTED', 'DECLINED');
            END IF;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            id          SERIAL PRIMARY KEY,
            hr_user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            candidate_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            message     TEXT,
            status      invitestatus NOT NULL DEFAULT 'PENDING',
            sent_at     TIMESTAMPTZ,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_invite_hr_candidate_job UNIQUE (hr_user_id, candidate_id, job_id)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_invites_hr_user_id ON invites (hr_user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_invites_candidate_id ON invites (candidate_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_invites_job_id ON invites (job_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS invites")
    op.execute("DROP TYPE IF EXISTS invitestatus")
