from pydantic import BaseModel

from app.schemas.resumes import CandidateProfileOut


class MatchScoreOut(BaseModel):
    total: float
    skill_overlap: float
    semantic: float
    experience_fit: float
    salary_fit: float
    location_fit: float
    matched_skills: list[str]
    missing_skills: list[str]


class RankedCandidateOut(BaseModel):
    candidate_id: int
    email: str
    profile: CandidateProfileOut
    score: MatchScoreOut
