from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.application import ApplicationStatus
from app.schemas.jobs import JobOut


class ApplicationCreate(BaseModel):
    job_id: int
    cover_letter: str | None = Field(None, max_length=5000)


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationOut(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    status: ApplicationStatus
    cover_letter: str | None
    match_score: Decimal | None
    created_at: datetime
    job: JobOut

    model_config = {"from_attributes": True}


class ApplicationListOut(BaseModel):
    total: int
    items: list[ApplicationOut]
