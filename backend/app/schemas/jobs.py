from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.job import EmploymentType, JobStatus


class CompanyOut(BaseModel):
    id: int
    name: str
    website: str | None = None

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=10)
    required_skills: list[str] = Field(default_factory=list)
    min_experience: int | None = Field(None, ge=0)
    max_experience: int | None = Field(None, ge=0)
    min_salary: Decimal | None = Field(None, ge=0)
    max_salary: Decimal | None = Field(None, ge=0)
    location: str | None = Field(None, max_length=255)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    company_name: str = Field(..., min_length=1, max_length=255)


class JobUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, min_length=10)
    required_skills: list[str] | None = None
    min_experience: int | None = Field(None, ge=0)
    max_experience: int | None = Field(None, ge=0)
    min_salary: Decimal | None = Field(None, ge=0)
    max_salary: Decimal | None = Field(None, ge=0)
    location: str | None = Field(None, max_length=255)
    employment_type: EmploymentType | None = None
    status: JobStatus | None = None


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    required_skills: list[str]
    min_experience: int | None
    max_experience: int | None
    min_salary: Decimal | None
    max_salary: Decimal | None
    location: str | None
    employment_type: EmploymentType
    status: JobStatus
    created_at: datetime
    company: CompanyOut

    model_config = {"from_attributes": True}


class JobListOut(BaseModel):
    total: int
    items: list[JobOut]
