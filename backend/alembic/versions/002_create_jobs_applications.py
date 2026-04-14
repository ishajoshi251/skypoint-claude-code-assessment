"""create companies, jobs, and applications tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id                  SERIAL PRIMARY KEY,
            name                VARCHAR(255) NOT NULL,
            website             VARCHAR(255),
            description         TEXT,
            created_by_user_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_companies_id ON companies (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_companies_created_by ON companies (created_by_user_id)")

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE jobstatus AS ENUM ('OPEN', 'CLOSED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE employmenttype AS ENUM ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id                  SERIAL PRIMARY KEY,
            company_id          INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            posted_by_user_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            title               VARCHAR(255) NOT NULL,
            description         TEXT NOT NULL,
            required_skills     TEXT[] NOT NULL DEFAULT '{}',
            min_experience      INTEGER,
            max_experience      INTEGER,
            min_salary          NUMERIC(12, 2),
            max_salary          NUMERIC(12, 2),
            location            VARCHAR(255),
            employment_type     employmenttype NOT NULL DEFAULT 'FULL_TIME',
            status              jobstatus NOT NULL DEFAULT 'OPEN',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_id ON jobs (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_company_id ON jobs (company_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_posted_by ON jobs (posted_by_user_id)")

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE applicationstatus AS ENUM (
                'APPLIED', 'SHORTLISTED', 'INTERVIEW', 'OFFERED', 'HIRED', 'REJECTED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id              SERIAL PRIMARY KEY,
            job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            candidate_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status          applicationstatus NOT NULL DEFAULT 'APPLIED',
            cover_letter    TEXT,
            match_score     NUMERIC(5, 2),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_application_job_candidate UNIQUE (job_id, candidate_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_id ON applications (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_job_id ON applications (job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_candidate_id ON applications (candidate_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS applications")
    op.execute("DROP TABLE IF EXISTS jobs")
    op.execute("DROP TABLE IF EXISTS companies")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS employmenttype")
