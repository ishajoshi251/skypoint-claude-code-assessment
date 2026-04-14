"""
Matching endpoints.

GET  /jobs/{job_id}/match-score          — Candidate: score of their profile vs this job
GET  /jobs/{job_id}/candidates/ranked    — HR: ranked candidate list for this job
"""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.candidate_profile import CandidateProfile
from app.models.job import Job, JobStatus
from app.models.user import Role, User
from app.schemas.matching import MatchScoreOut, RankedCandidateOut
from app.schemas.resumes import CandidateProfileOut
from app.services.matching_service import MatchScore, compute_match_score, rank_candidates

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["matching"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_job_or_404(job_id: int, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job")
    return job


def _score_to_out(score: MatchScore) -> MatchScoreOut:
    return MatchScoreOut(
        total=score.total,
        skill_overlap=score.skill_overlap,
        semantic=score.semantic,
        experience_fit=score.experience_fit,
        salary_fit=score.salary_fit,
        location_fit=score.location_fit,
        matched_skills=score.matched_skills,
        missing_skills=score.missing_skills,
    )


# ---------------------------------------------------------------------------
# Candidate: get own match score against a job
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/match-score", response_model=MatchScoreOut)
async def get_my_match_score(
    job_id: int,
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchScoreOut:
    """Returns the calling candidate's match score breakdown against the given job."""
    job = await _get_job_or_404(job_id, db)

    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        # Return zeroed score — profile not set up yet
        return MatchScoreOut(
            total=0.0, skill_overlap=0.0, semantic=0.0,
            experience_fit=0.0, salary_fit=0.0, location_fit=0.0,
            matched_skills=[], missing_skills=list(job.required_skills or []),
        )

    score = compute_match_score(job, profile)
    return _score_to_out(score)


# ---------------------------------------------------------------------------
# HR: ranked candidate list for a job
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/candidates/ranked", response_model=list[RankedCandidateOut])
async def get_ranked_candidates(
    job_id: int,
    current_user: Annotated[User, Depends(require_role(Role.HR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    min_score: float = 0.0,
    limit: int = 50,
) -> list[RankedCandidateOut]:
    """
    Returns all candidates with a complete profile, ranked by match score.
    HR only. No restriction to own-company jobs — HR can use this for any open job.
    """
    job = await _get_job_or_404(job_id, db)
    if job.status != JobStatus.OPEN:
        raise ForbiddenError("Can only rank candidates for open jobs.")

    # Load all candidate profiles (with their linked user for email)
    result = await db.execute(
        select(CandidateProfile).options(selectinload(CandidateProfile.user))
    )
    profiles: list[CandidateProfile] = list(result.scalars().all())

    ranked = rank_candidates(job, profiles)

    out: list[RankedCandidateOut] = []
    for r in ranked:
        if r.score.total < min_score:
            continue
        out.append(
            RankedCandidateOut(
                candidate_id=r.candidate_id,
                email=r.profile.user.email,
                profile=CandidateProfileOut.model_validate(r.profile),
                score=_score_to_out(r.score),
            )
        )
        if len(out) >= limit:
            break

    return out
