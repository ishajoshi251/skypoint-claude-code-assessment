"""003 resumes and expanded candidate_profiles

Revision ID: 003
Revises: 002
Create Date: 2026-04-14
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # resumes table
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id               SERIAL PRIMARY KEY,
            candidate_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            file_path        VARCHAR(512) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            mime_type        VARCHAR(100) NOT NULL,
            parsed_text      TEXT,
            parsed_skills    TEXT[],
            parsed_experience_years FLOAT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_resumes_id ON resumes (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resumes_candidate_id ON resumes (candidate_id)")

    # ------------------------------------------------------------------
    # Expand candidate_profiles
    # ------------------------------------------------------------------
    # Add each column only if it doesn't already exist (idempotent)
    _add_column_if_missing = """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='candidate_profiles' AND column_name='{col}'
            ) THEN
                ALTER TABLE candidate_profiles ADD COLUMN {col} {definition};
            END IF;
        END $$;
    """

    columns = [
        ("full_name",              "VARCHAR(255)"),
        ("headline",               "VARCHAR(255)"),
        ("location",               "VARCHAR(255)"),
        ("bio",                    "TEXT"),
        ("years_experience",       "NUMERIC(4,1)"),
        ("current_salary",         "NUMERIC(12,2)"),
        ("expected_salary",        "NUMERIC(12,2)"),
        ("notice_period_days",     "INTEGER"),
        ("skills",                 "TEXT[]"),
        ("resume_id",              "INTEGER REFERENCES resumes(id) ON DELETE SET NULL"),
    ]
    for col, defn in columns:
        op.execute(_add_column_if_missing.format(col=col, definition=defn))


def downgrade() -> None:
    # Drop columns from candidate_profiles
    for col in [
        "resume_id", "skills", "notice_period_days", "expected_salary",
        "current_salary", "years_experience", "bio", "location", "headline", "full_name",
    ]:
        op.execute(f"ALTER TABLE candidate_profiles DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TABLE IF EXISTS resumes")
