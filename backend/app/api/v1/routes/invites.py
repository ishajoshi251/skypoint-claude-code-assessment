"""
Invites routes — HR bulk invite + status management.

POST  /invites/bulk            — HR sends personalised invite emails to N candidates.
GET   /invites                 — HR views all invites they sent (filterable by job).
GET   /invites/received        — Candidate views invites they received.
PATCH /invites/{id}/status     — Candidate accepts or declines an invite.
"""
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.candidate_profile import CandidateProfile
from app.models.invite import Invite, InviteStatus
from app.models.job import Job
from app.models.user import Role, User
from app.schemas.invites import BulkInviteRequest, BulkInviteResult, InviteOut
from app.services.email_service import build_invite_email, send_email
from app.services.matching_service import compute_match_score

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/invites", tags=["invites"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_job_or_404(job_id: int, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job")
    return job


async def _load_candidate_profile(
    db: AsyncSession, user_id: int
) -> CandidateProfile | None:
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Bulk invite
# ---------------------------------------------------------------------------


@router.post("/bulk", response_model=BulkInviteResult, status_code=201)
async def bulk_invite(
    body: BulkInviteRequest,
    current_user: Annotated[User, Depends(require_role(Role.HR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkInviteResult:
    """
    Send personalised invite emails to a list of candidates for a job.

    - Skips candidates that already have an invite for this job.
    - Generates a per-candidate email referencing their matched skills.
    - Emails are sent via MailHog (captured in dev; visible at localhost:8025).
    - A failed email send still creates the invite record (status stays PENDING).
    """
    job = await _get_job_or_404(body.job_id, db)

    # Validate HR owns the job
    if job.posted_by_user_id != current_user.id:
        raise ForbiddenError("You can only invite candidates for your own jobs.")

    # Check for duplicate invites in a single query
    existing_result = await db.execute(
        select(Invite.candidate_id).where(
            Invite.hr_user_id == current_user.id,
            Invite.job_id == body.job_id,
            Invite.candidate_id.in_(body.candidate_ids),
        )
    )
    already_invited = {row[0] for row in existing_result.all()}

    invited: list[InviteOut] = []
    skipped: list[int] = []
    failed: list[int] = []

    for candidate_id in body.candidate_ids:
        if candidate_id in already_invited:
            skipped.append(candidate_id)
            continue

        # Load candidate user + profile
        cand_result = await db.execute(select(User).where(User.id == candidate_id))
        candidate_user: User | None = cand_result.scalar_one_or_none()
        if candidate_user is None or candidate_user.role != Role.CANDIDATE:
            skipped.append(candidate_id)
            continue

        profile = await _load_candidate_profile(db, candidate_id)

        # Compute match score for personalised email content
        matched_skills: list[str] = []
        total_score = 0.0
        if profile:
            ms = compute_match_score(job, profile)
            matched_skills = ms.matched_skills
            total_score = ms.total

        # Create invite record
        invite = Invite(
            hr_user_id=current_user.id,
            candidate_id=candidate_id,
            job_id=body.job_id,
            message=body.message,
            status=InviteStatus.PENDING,
        )
        db.add(invite)
        await db.flush()  # get invite.id

        # Build and send personalised email
        candidate_name = (
            profile.full_name if profile and profile.full_name
            else candidate_user.email.split("@")[0]
        )
        company_name = job.company.name if hasattr(job, "company") and job.company else "us"

        # Eagerly load company if not already loaded
        if not hasattr(job, "_company_loaded"):
            from sqlalchemy.orm import selectinload
            job_with_company = await db.execute(
                select(Job).where(Job.id == job.id).options(selectinload(Job.company))
            )
            job_loaded = job_with_company.scalar_one_or_none()
            if job_loaded and job_loaded.company:
                company_name = job_loaded.company.name

        subject, html_body = build_invite_email(
            candidate_name=candidate_name,
            job_title=job.title,
            company_name=company_name,
            matched_skills=matched_skills,
            match_score=total_score,
            custom_message=body.message,
        )

        email_sent = await send_email(
            to_address=candidate_user.email,
            subject=subject,
            html_body=html_body,
        )

        if email_sent:
            invite.status = InviteStatus.SENT
            invite.sent_at = datetime.now(timezone.utc)
        else:
            failed.append(candidate_id)

        invited.append(InviteOut.model_validate(invite))

    await db.commit()

    logger.info(
        "Bulk invite complete",
        hr_user_id=current_user.id,
        job_id=body.job_id,
        invited=len(invited),
        skipped=len(skipped),
        failed=len(failed),
    )
    return BulkInviteResult(invited=invited, skipped=skipped, failed=failed)


# ---------------------------------------------------------------------------
# HR: list sent invites
# ---------------------------------------------------------------------------


@router.get("", response_model=list[InviteOut])
async def list_sent_invites(
    current_user: Annotated[User, Depends(require_role(Role.HR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[InviteOut]:
    """HR lists invites they sent, optionally filtered by job."""
    q = select(Invite).where(Invite.hr_user_id == current_user.id)
    if job_id is not None:
        q = q.where(Invite.job_id == job_id)
    q = q.order_by(Invite.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [InviteOut.model_validate(i) for i in result.scalars().all()]


# ---------------------------------------------------------------------------
# Candidate: list received invites
# ---------------------------------------------------------------------------


@router.get("/received", response_model=list[InviteOut])
async def list_received_invites(
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[InviteOut]:
    """Candidate lists invites they received."""
    result = await db.execute(
        select(Invite)
        .where(Invite.candidate_id == current_user.id)
        .order_by(Invite.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [InviteOut.model_validate(i) for i in result.scalars().all()]


# ---------------------------------------------------------------------------
# Candidate: accept / decline invite
# ---------------------------------------------------------------------------


class InviteStatusUpdate(BaseModel):
    status: InviteStatus


@router.patch("/{invite_id}/status", response_model=InviteOut)
async def update_invite_status(
    invite_id: int,
    body: InviteStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InviteOut:
    """Candidate accepts or declines an invite. HR cannot use this endpoint."""
    if current_user.role != Role.CANDIDATE:
        raise ForbiddenError("Only candidates can respond to invites.")

    result = await db.execute(select(Invite).where(Invite.id == invite_id))
    invite: Invite | None = result.scalar_one_or_none()
    if invite is None:
        raise NotFoundError("Invite")
    if invite.candidate_id != current_user.id:
        raise ForbiddenError()
    if body.status not in (InviteStatus.ACCEPTED, InviteStatus.DECLINED):
        raise ValidationError("Status must be ACCEPTED or DECLINED.")

    invite.status = body.status
    await db.commit()
    await db.refresh(invite)
    return InviteOut.model_validate(invite)
