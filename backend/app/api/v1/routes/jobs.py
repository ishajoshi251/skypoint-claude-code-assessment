"""
Jobs routes — CRUD for job postings.
Write operations (create/update/delete) are HR-only.
Read operations are public (any authenticated user).
"""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query

logger = structlog.get_logger(__name__)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.company import Company
from app.models.job import Job, JobStatus
from app.models.user import Role, User
from app.schemas.jobs import JobCreate, JobListOut, JobOut, JobUpdate
from app.services.embedding_service import build_job_text, embed_text

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _get_job_or_404(job_id: int, db: AsyncSession) -> Job:
    result = await db.execute(
        select(Job).where(Job.id == job_id).options(selectinload(Job.company))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job")
    return job


def _assert_hr_owns_job(job: Job, user: User) -> None:
    """HR can only modify jobs posted by themselves."""
    if job.posted_by_user_id != user.id:
        raise ForbiddenError("You can only modify jobs you posted.")


@router.post("", response_model=JobOut, status_code=201)
async def create_job(
    body: JobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(Role.HR))],
) -> Job:
    # Upsert company by name (scoped to this HR user)
    result = await db.execute(
        select(Company).where(
            Company.name == body.company_name,
            Company.created_by_user_id == current_user.id,
        )
    )
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(name=body.company_name, created_by_user_id=current_user.id)
        db.add(company)
        await db.flush()

    job = Job(
        company_id=company.id,
        posted_by_user_id=current_user.id,
        title=body.title,
        description=body.description,
        required_skills=body.required_skills,
        min_experience=body.min_experience,
        max_experience=body.max_experience,
        min_salary=body.min_salary,
        max_salary=body.max_salary,
        location=body.location,
        employment_type=body.employment_type,
    )
    db.add(job)
    await db.flush()  # get job.id before embedding

    # Compute and store embedding (non-blocking via executor)
    try:
        text = build_job_text(job.title, job.description, job.required_skills)
        job.embedding = await embed_text(text)
    except Exception:
        logger.warning("Embedding failed for new job", job_id=job.id)

    await db.commit()
    await db.refresh(job)

    # Load company relationship for response
    await db.refresh(job, ["company"])
    return job


@router.get("", response_model=JobListOut)
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    status: JobStatus | None = Query(None),
    location: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> JobListOut:
    q = select(Job).options(selectinload(Job.company)).where(Job.status == JobStatus.OPEN)
    if status is not None:
        q = select(Job).options(selectinload(Job.company)).where(Job.status == status)
    if location:
        q = q.where(Job.location.ilike(f"%{location}%"))

    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(q.order_by(Job.created_at.desc()).offset(skip).limit(limit))
    items = list(result.scalars().all())
    return JobListOut(total=total, items=items)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Job:
    return await _get_job_or_404(job_id, db)


@router.patch("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: int,
    body: JobUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(Role.HR))],
) -> Job:
    job = await _get_job_or_404(job_id, db)
    _assert_hr_owns_job(job, current_user)

    updated_fields = body.model_dump(exclude_unset=True)
    for field, value in updated_fields.items():
        setattr(job, field, value)

    # Re-embed if description, title, or skills changed
    if updated_fields.keys() & {"title", "description", "required_skills"}:
        try:
            text = build_job_text(job.title, job.description, job.required_skills)
            job.embedding = await embed_text(text)
        except Exception:
            logger.warning("Re-embedding failed for job", job_id=job.id)

    await db.commit()
    await db.refresh(job, ["company"])
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(Role.HR))],
) -> None:
    job = await _get_job_or_404(job_id, db)
    _assert_hr_owns_job(job, current_user)
    await db.delete(job)
    await db.commit()
