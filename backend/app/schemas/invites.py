from datetime import datetime

from pydantic import BaseModel, Field

from app.models.invite import InviteStatus
from app.schemas.matching import MatchScoreOut
from app.schemas.resumes import CandidateProfileOut


class BulkInviteRequest(BaseModel):
    """HR sends invites to multiple candidates for a specific job."""
    job_id: int
    candidate_ids: list[int] = Field(..., min_length=1, max_length=50)
    message: str | None = Field(None, max_length=1000)


class InviteOut(BaseModel):
    id: int
    hr_user_id: int
    candidate_id: int
    job_id: int
    message: str | None
    status: InviteStatus
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkInviteResult(BaseModel):
    """Summary of a bulk invite operation."""
    invited: list[InviteOut]
    skipped: list[int]  # candidate_ids that already had an invite for this job
    failed: list[int]   # candidate_ids where email send failed (invite still created)


# Used for the smart-search response — includes match score alongside candidate info
class CandidateSearchResult(BaseModel):
    candidate_id: int
    email: str
    profile: CandidateProfileOut
    score: MatchScoreOut

    model_config = {"from_attributes": True}


class CandidateSearchRequest(BaseModel):
    """HR can search by passing a free-text JD and/or structured filters."""
    job_id: int | None = Field(None, description="Use an existing job as the query basis")
    query_text: str | None = Field(
        None, max_length=5000,
        description="Free-text job description to match candidates against"
    )
    required_skills: list[str] = Field(default_factory=list)
    min_experience: float | None = None
    max_experience: float | None = None
    max_salary: float | None = None
    location: str | None = None
    min_score: float = Field(0.0, ge=0.0, le=100.0)
    limit: int = Field(20, ge=1, le=100)
