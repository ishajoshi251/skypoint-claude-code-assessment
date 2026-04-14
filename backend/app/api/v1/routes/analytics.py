"""
Analytics endpoints — HR-only.

All queries are scoped to the requesting HR user's own posted jobs.
The skills heatmap aggregates across all open jobs in the system.
"""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.models.application import Application, ApplicationStatus
from app.models.job import Job, JobStatus
from app.models.user import Role, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Response helpers (inline Pydantic models kept small)
# ---------------------------------------------------------------------------
from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total_jobs: int
    open_jobs: int
    total_applications: int
    avg_match_score: float | None
    hired_count: int
    active_pipeline: int  # APPLIED + SHORTLISTED + INTERVIEW + OFFERED


class JobFunnelRow(BaseModel):
    job_id: int
    job_title: str
    company: str
    status: str
    applied: int
    shortlisted: int
    interview: int
    offered: int
    hired: int
    rejected: int
    total: int


class SkillDemand(BaseModel):
    skill: str
    count: int


# ---------------------------------------------------------------------------
# GET /analytics/summary
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.HR)),
):
    """Overview stats for the current HR user's own posted jobs."""
    # Fetch HR's jobs
    jobs_result = await db.execute(
        select(Job).where(Job.posted_by_user_id == current_user.id)
    )
    jobs = jobs_result.scalars().all()
    job_ids = [j.id for j in jobs]

    open_jobs = sum(1 for j in jobs if j.status == JobStatus.OPEN)

    if not job_ids:
        return AnalyticsSummary(
            total_jobs=0,
            open_jobs=0,
            total_applications=0,
            avg_match_score=None,
            hired_count=0,
            active_pipeline=0,
        )

    # Fetch all applications across those jobs
    apps_result = await db.execute(
        select(Application).where(Application.job_id.in_(job_ids))
    )
    apps = apps_result.scalars().all()

    scores = [float(a.match_score) for a in apps if a.match_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    hired = sum(1 for a in apps if a.status == ApplicationStatus.HIRED)
    active = sum(
        1
        for a in apps
        if a.status
        in {
            ApplicationStatus.APPLIED,
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFERED,
        }
    )

    return AnalyticsSummary(
        total_jobs=len(jobs),
        open_jobs=open_jobs,
        total_applications=len(apps),
        avg_match_score=avg_score,
        hired_count=hired,
        active_pipeline=active,
    )


# ---------------------------------------------------------------------------
# GET /analytics/funnel
# ---------------------------------------------------------------------------
@router.get("/funnel", response_model=list[JobFunnelRow])
async def get_funnel(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.HR)),
):
    """Per-job application funnel for the current HR user's jobs."""
    from app.models.company import Company

    jobs_result = await db.execute(
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(Job.posted_by_user_id == current_user.id)
        .order_by(Job.created_at.desc())
    )
    job_rows = jobs_result.all()

    if not job_rows:
        return []

    job_ids = [j.id for j, _ in job_rows]

    apps_result = await db.execute(
        select(Application).where(Application.job_id.in_(job_ids))
    )
    apps = apps_result.scalars().all()

    # Group by job_id
    by_job: dict[int, list[Application]] = {}
    for a in apps:
        by_job.setdefault(a.job_id, []).append(a)

    funnel = []
    for job, company in job_rows:
        job_apps = by_job.get(job.id, [])
        counts = Counter(a.status for a in job_apps)
        funnel.append(
            JobFunnelRow(
                job_id=job.id,
                job_title=job.title,
                company=company.name,
                status=job.status.value,
                applied=counts.get(ApplicationStatus.APPLIED, 0),
                shortlisted=counts.get(ApplicationStatus.SHORTLISTED, 0),
                interview=counts.get(ApplicationStatus.INTERVIEW, 0),
                offered=counts.get(ApplicationStatus.OFFERED, 0),
                hired=counts.get(ApplicationStatus.HIRED, 0),
                rejected=counts.get(ApplicationStatus.REJECTED, 0),
                total=len(job_apps),
            )
        )

    return funnel


# ---------------------------------------------------------------------------
# GET /analytics/skills
# ---------------------------------------------------------------------------
@router.get("/skills", response_model=list[SkillDemand])
async def get_skill_demand(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.HR)),
):
    """Most in-demand skills across all currently open jobs (system-wide)."""
    result = await db.execute(
        select(Job.required_skills).where(Job.status == JobStatus.OPEN)
    )
    all_skills: list[str] = []
    for (skills,) in result:
        if skills:
            all_skills.extend(s.strip() for s in skills if s.strip())

    counts = Counter(all_skills)
    return [
        SkillDemand(skill=skill, count=count)
        for skill, count in counts.most_common(20)
    ]
