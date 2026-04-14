from datetime import datetime

from pydantic import BaseModel, Field


class ResumeOut(BaseModel):
    id: int
    candidate_id: int
    original_filename: str
    mime_type: str
    parsed_skills: list[str] | None = None
    parsed_experience_years: float | None = None
    # parsed_text intentionally omitted from list — too large; available via detail endpoint
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetailOut(ResumeOut):
    parsed_text: str | None = None


class CandidateProfileUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    headline: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=255)
    bio: str | None = Field(None, max_length=2000)
    years_experience: float | None = Field(None, ge=0, le=50)
    current_salary: float | None = Field(None, ge=0)
    expected_salary: float | None = Field(None, ge=0)
    notice_period_days: int | None = Field(None, ge=0, le=365)
    skills: list[str] | None = Field(None, max_length=100)


class CandidateProfileOut(BaseModel):
    id: int
    user_id: int
    full_name: str | None = None
    headline: str | None = None
    location: str | None = None
    bio: str | None = None
    years_experience: float | None = None
    current_salary: float | None = None
    expected_salary: float | None = None
    notice_period_days: int | None = None
    skills: list[str] | None = None
    resume_id: int | None = None

    model_config = {"from_attributes": True}
