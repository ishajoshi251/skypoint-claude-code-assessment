"""
Applications routes.
- POST /applications          — Candidate applies to a job (once per job, 409 on duplicate)
- GET  /applications/me       — Candidate views their own applications
- GET  /jobs/{job_id}/applications — HR views all applicants for their job
- PATCH /applications/{id}/status  — HR moves candidate through pipeline
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_role
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.application import Application
from app.models.job import Job
from app.models.user import Role, User
from app.schemas.applications import (
    ApplicationCreate,
    ApplicationListOut,
    ApplicationOut,
    ApplicationStatusUpdate,
)

router = APIRouter(tags=["applications"])


async def _get_application_or_404(app_id: int, db: AsyncSession) -> Application:
    result = await db.execute(
        select(Application)
        .where(Application.id == app_id)
        .options(selectinload(Application.job).selectinload(Job.company))
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise NotFoundError("Application")
    return app


# ---------------------------------------------------------------------------
# Candidate: apply to a job
# ---------------------------------------------------------------------------

@router.post("/applications", response_model=ApplicationOut, status_code=201)
async def apply_to_job(
    body: ApplicationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
) -> Application:
    # Verify job exists
    result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job")

    application = Application(
        job_id=body.job_id,
        candidate_id=current_user.id,
        cover_letter=body.cover_letter,
    )
    db.add(application)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("You have already applied to this job.")

    await db.refresh(application)
    # Load nested relationships for response
    result = await db.execute(
        select(Application)
        .where(Application.id == application.id)
        .options(selectinload(Application.job).selectinload(Job.company))
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Candidate: view own applications
# ---------------------------------------------------------------------------

@router.get("/applications/me", response_model=ApplicationListOut)
async def my_applications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ApplicationListOut:
    q = (
        select(Application)
        .where(Application.candidate_id == current_user.id)
        .options(selectinload(Application.job).selectinload(Job.company))
    )
    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        q.order_by(Application.created_at.desc()).offset(skip).limit(limit)
    )
    return ApplicationListOut(total=total, items=list(result.scalars().all()))


# ---------------------------------------------------------------------------
# HR: view applicants for a job
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}/applications", response_model=ApplicationListOut)
async def job_applications(
    job_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(Role.HR))],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ApplicationListOut:
    # Verify job exists and belongs to this HR
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job")
    if job.posted_by_user_id != current_user.id:
        raise ForbiddenError("You can only view applications for your own jobs.")

    q = (
        select(Application)
        .where(Application.job_id == job_id)
        .options(selectinload(Application.job).selectinload(Job.company))
    )
    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        q.order_by(Application.created_at.desc()).offset(skip).limit(limit)
    )
    return ApplicationListOut(total=total, items=list(result.scalars().all()))


# ---------------------------------------------------------------------------
# HR: update application status (pipeline moves)
# ---------------------------------------------------------------------------

@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
async def update_application_status(
    application_id: int,
    body: ApplicationStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(Role.HR))],
) -> Application:
    application = await _get_application_or_404(application_id, db)

    # Verify HR owns the job this application belongs to
    if application.job.posted_by_user_id != current_user.id:
        raise ForbiddenError("You can only update applications for your own jobs.")

    application.status = body.status
    await db.commit()
    await db.refresh(application)

    result = await db.execute(
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.job).selectinload(Job.company))
    )
    return result.scalar_one()
