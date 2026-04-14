"""004 add embedding columns to jobs and candidate_profiles

Revision ID: 004
Revises: 003
Create Date: 2026-04-14
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

_ADD_COL = """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='{table}' AND column_name='embedding'
        ) THEN
            ALTER TABLE {table} ADD COLUMN embedding vector(384);
        END IF;
    END $$;
"""


def upgrade() -> None:
    # Ensure pgvector extension exists (migration 001 already does this,
    # but guard here too so this migration is independently rerunnable)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(_ADD_COL.format(table="jobs"))
    op.execute(_ADD_COL.format(table="candidate_profiles"))

    # HNSW index for approximate nearest-neighbour search on jobs
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_jobs_embedding_hnsw
        ON jobs USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    # HNSW index on candidate profiles
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_candidate_profiles_embedding_hnsw
        ON candidate_profiles USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_candidate_profiles_embedding_hnsw")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE candidate_profiles DROP COLUMN IF EXISTS embedding")
