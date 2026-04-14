"""
Matching service — hybrid TF-IDF keyword + semantic similarity scoring.

Score breakdown (weights):
  skill_overlap  30%  — % of required job skills present in candidate skills
  semantic       40%  — cosine similarity of sentence embeddings × 100
  experience_fit 15%  — how well candidate YOE fits the job range
  salary_fit     10%  — candidate expected salary vs job max salary
  location_fit    5%  — rough location string match

Total is 0–100. Higher = better match.
"""
from dataclasses import dataclass, field

import numpy as np

from app.models.candidate_profile import CandidateProfile
from app.models.job import Job


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class MatchScore:
    total: float           # 0–100
    skill_overlap: float   # 0–100
    semantic: float        # 0–100
    experience_fit: float  # 0–100
    salary_fit: float      # 0–100
    location_fit: float    # 0–100
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)


@dataclass
class RankedCandidate:
    candidate_id: int
    profile: CandidateProfile
    score: MatchScore


# ---------------------------------------------------------------------------
# Individual dimension scorers
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Dot product of two L2-normalised vectors (already normalised by encode())."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    dot = float(np.dot(va, vb))
    return max(0.0, min(1.0, dot))


def _skill_overlap(
    job_skills: list[str],
    candidate_skills: list[str],
) -> tuple[float, list[str], list[str]]:
    job_set = {s.lower().strip() for s in (job_skills or [])}
    cand_set = {s.lower().strip() for s in (candidate_skills or [])}
    if not job_set:
        return 100.0, [], []
    matched = sorted(job_set & cand_set)
    missing = sorted(job_set - cand_set)
    score = len(matched) / len(job_set) * 100.0
    return round(score, 1), matched, missing


def _experience_fit(
    min_exp: int | None,
    max_exp: int | None,
    candidate_years: float | None,
) -> float:
    if candidate_years is None:
        return 50.0  # unknown — neutral
    if min_exp is None and max_exp is None:
        return 100.0  # no requirement
    lo = min_exp or 0
    hi = max_exp if max_exp is not None else 999
    if lo <= candidate_years <= hi:
        return 100.0
    if candidate_years < lo:
        gap = lo - candidate_years
        return round(max(0.0, 100.0 - gap * 15.0), 1)
    # Overqualified — penalise gently (overqualified is still viable)
    gap = candidate_years - hi
    return round(max(60.0, 100.0 - gap * 5.0), 1)


def _salary_fit(max_salary: float | None, expected_salary: float | None) -> float:
    if max_salary is None or expected_salary is None:
        return 75.0  # unknown — slightly positive
    if expected_salary <= max_salary:
        return 100.0
    over_ratio = (expected_salary - max_salary) / max_salary
    return round(max(0.0, 100.0 - over_ratio * 100.0), 1)


def _location_fit(job_location: str | None, candidate_location: str | None) -> float:
    if not job_location or not candidate_location:
        return 75.0  # unknown
    j = job_location.lower()
    c = candidate_location.lower()
    if j in c or c in j:
        return 100.0
    if "remote" in j or "remote" in c:
        return 90.0
    # Check city-level match (first comma-separated token)
    j_city = j.split(",")[0].strip()
    c_city = c.split(",")[0].strip()
    if j_city and c_city and (j_city in c_city or c_city in j_city):
        return 85.0
    return 40.0


# ---------------------------------------------------------------------------
# Primary scoring function
# ---------------------------------------------------------------------------


def compute_match_score(job: Job, profile: CandidateProfile) -> MatchScore:
    """Compute a hybrid match score for a (job, candidate_profile) pair."""
    skill_score, matched, missing = _skill_overlap(
        job.required_skills or [], profile.skills or []
    )

    # Semantic similarity — fall back to skill score if embeddings absent
    if job.embedding and profile.embedding:
        sem_score = round(_cosine_similarity(job.embedding, profile.embedding) * 100.0, 1)
    else:
        sem_score = skill_score

    exp_score = _experience_fit(
        job.min_experience,
        job.max_experience,
        float(profile.years_experience) if profile.years_experience is not None else None,
    )
    sal_score = _salary_fit(
        float(job.max_salary) if job.max_salary is not None else None,
        float(profile.expected_salary) if profile.expected_salary is not None else None,
    )
    loc_score = _location_fit(job.location, profile.location)

    total = round(
        skill_score * 0.30
        + sem_score * 0.40
        + exp_score * 0.15
        + sal_score * 0.10
        + loc_score * 0.05,
        1,
    )

    return MatchScore(
        total=total,
        skill_overlap=skill_score,
        semantic=sem_score,
        experience_fit=exp_score,
        salary_fit=sal_score,
        location_fit=loc_score,
        matched_skills=matched,
        missing_skills=missing,
    )


def rank_candidates(job: Job, profiles: list[CandidateProfile]) -> list[RankedCandidate]:
    """Score and rank a list of candidate profiles against a job, descending by total."""
    ranked = [
        RankedCandidate(
            candidate_id=p.user_id,
            profile=p,
            score=compute_match_score(job, p),
        )
        for p in profiles
    ]
    ranked.sort(key=lambda r: r.score.total, reverse=True)
    return ranked
