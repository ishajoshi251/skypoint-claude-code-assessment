"""
Candidates routes — HR-only search and discovery endpoints.

POST  /candidates/search   — Smart-search: match candidates against a JD or job_id.
GET   /candidates          — Paginated list of all candidates (HR only).
GET   /candidates/{id}     — HR views a single candidate profile.
"""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.core.exceptions import NotFoundError, ValidationError
from app.models.candidate_profile import CandidateProfile
from app.models.job import Job, JobStatus
from app.models.user import Role, User
from app.schemas.invites import CandidateSearchRequest, CandidateSearchResult
from app.schemas.resumes import CandidateProfileOut
from app.services.embedding_service import build_job_text, embed_text
from app.services.matching_service import compute_match_score

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/candidates", tags=["candidates"])


async def _load_all_profiles(db: AsyncSession) -> list[CandidateProfile]:
    result = await db.execute(select(CandidateProfile))
    return list(result.scalars().all())


async def _load_users_by_ids(
    db: AsyncSession, user_ids: list[int]
) -> dict[int, User]:
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}


# ---------------------------------------------------------------------------
# Smart search — core feature
# ---------------------------------------------------------------------------


@router.post("/search", response_model=list[CandidateSearchResult])
async def smart_search(
    body: CandidateSearchRequest,
    current_user: Annotated[User, Depends(require_role(Role.HR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CandidateSearchResult]:
    """
    Match all candidates against a job or free-text query.

    Priority order for query basis:
    1. If job_id provided → use that job's embeddings + structured fields.
    2. If query_text provided → generate a transient embedding on-the-fly.
    3. Structured filters alone (required_skills, experience, salary, location).
    """
    if not body.job_id and not body.query_text and not body.required_skills:
        raise ValidationError(
            "Provide at least one of: job_id, query_text, or required_skills."
        )

    # --- Build a virtual Job object to score against ---
    if body.job_id is not None:
        result = await db.execute(select(Job).where(Job.id == body.job_id))
        job: Job | None = result.scalar_one_or_none()
        if job is None:
            raise NotFoundError("Job")
        # Merge any extra filters the HR specified on top of the stored job
        virtual_job = job
    else:
        # Construct a lightweight virtual Job (not persisted)
        virtual_job = Job.__new__(Job)
        virtual_job.id = 0
        virtual_job.title = "Smart Search Query"
        virtual_job.description = body.query_text or ""
        virtual_job.required_skills = body.required_skills
        virtual_job.min_experience = body.min_experience
        virtual_job.max_experience = body.max_experience
        virtual_job.min_salary = None
        virtual_job.max_salary = body.max_salary
        virtual_job.location = body.location
        virtual_job.status = JobStatus.OPEN
        virtual_job.embedding = None

        # Embed the query text for semantic scoring
        if body.query_text:
            try:
                text = build_job_text(
                    virtual_job.title,
                    virtual_job.description,
                    virtual_job.required_skills,
                )
                virtual_job.embedding = await embed_text(text)
            except Exception:
                logger.warning("Embedding failed for smart search query")

    # --- Load all candidate profiles + their users ---
    profiles = await _load_all_profiles(db)
    if not profiles:
        return []

    user_map = await _load_users_by_ids(db, [p.user_id for p in profiles])

    # --- Score and filter ---
    results: list[CandidateSearchResult] = []
    for profile in profiles:
        user = user_map.get(profile.user_id)
        if user is None:
            continue

        score = compute_match_score(virtual_job, profile)
        if score.total < body.min_score:
            continue

        results.append(
            CandidateSearchResult(
                candidate_id=profile.user_id,
                email=user.email,
                full_name=profile.full_name,
                headline=profile.headline,
                location=profile.location,
                skills=profile.skills or [],
                years_experience=(
                    float(profile.years_experience)
                    if profile.years_experience is not None
                    else None
                ),
                score=score,
            )
        )

    # Sort by total score descending
    results.sort(key=lambda r: r.score.total, reverse=True)
    return results[: body.limit]


# ---------------------------------------------------------------------------
# List all candidates (paginated)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[CandidateProfileOut])
async def list_candidates(
    current_user: Annotated[User, Depends(require_role(Role.HR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[CandidateProfileOut]:
    """HR can paginate through all candidate profiles."""
    result = await db.execute(
        select(CandidateProfile).offset(skip).limit(limit)
    )
    profiles = result.scalars().all()
    return [CandidateProfileOut.model_validate(p) for p in profiles]


# ---------------------------------------------------------------------------
# Get single candidate
# ---------------------------------------------------------------------------


@router.get("/{candidate_id}", response_model=CandidateProfileOut)
async def get_candidate(
    candidate_id: int,
    current_user: Annotated[User, Depends(require_role(Role.HR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateProfileOut:
    """HR views a single candidate's profile."""
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == candidate_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Candidate profile")
    return CandidateProfileOut.model_validate(profile)
