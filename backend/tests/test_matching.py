"""
Tests for the matching service (unit) and matching API endpoints (integration).
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.models.candidate_profile import CandidateProfile
from app.models.job import Job, JobStatus, EmploymentType
from app.services.matching_service import (
    compute_match_score,
    rank_candidates,
    _skill_overlap,
    _experience_fit,
    _salary_fit,
    _location_fit,
)


# ---------------------------------------------------------------------------
# Unit tests — pure matching logic (no DB, no HTTP)
# ---------------------------------------------------------------------------


def _make_job(**kwargs) -> Job:
    """Create a minimal Job ORM object for testing (no DB session)."""
    j = Job.__new__(Job)
    j.id = kwargs.get("id", 1)
    j.title = kwargs.get("title", "Software Engineer")
    j.description = kwargs.get("description", "Build stuff")
    j.required_skills = kwargs.get("required_skills", [])
    j.min_experience = kwargs.get("min_experience", None)
    j.max_experience = kwargs.get("max_experience", None)
    j.min_salary = kwargs.get("min_salary", None)
    j.max_salary = kwargs.get("max_salary", None)
    j.location = kwargs.get("location", None)
    j.status = kwargs.get("status", JobStatus.OPEN)
    j.employment_type = kwargs.get("employment_type", EmploymentType.FULL_TIME)
    j.embedding = kwargs.get("embedding", None)
    return j


def _make_profile(**kwargs) -> CandidateProfile:
    p = CandidateProfile.__new__(CandidateProfile)
    p.id = kwargs.get("id", 1)
    p.user_id = kwargs.get("user_id", 1)
    p.skills = kwargs.get("skills", [])
    p.years_experience = kwargs.get("years_experience", None)
    p.expected_salary = kwargs.get("expected_salary", None)
    p.location = kwargs.get("location", None)
    p.headline = kwargs.get("headline", None)
    p.bio = kwargs.get("bio", None)
    p.embedding = kwargs.get("embedding", None)
    return p


class TestSkillOverlap:
    def test_full_match(self):
        score, matched, missing = _skill_overlap(["python", "aws"], ["python", "aws", "docker"])
        assert score == 100.0
        assert set(matched) == {"python", "aws"}
        assert missing == []

    def test_partial_match(self):
        score, matched, missing = _skill_overlap(["python", "aws", "k8s"], ["python"])
        assert round(score, 1) == round(100 / 3, 1)
        assert matched == ["python"]
        assert set(missing) == {"aws", "k8s"}

    def test_no_job_skills_returns_100(self):
        score, _, _ = _skill_overlap([], ["python"])
        assert score == 100.0

    def test_case_insensitive(self):
        score, _, _ = _skill_overlap(["Python", "AWS"], ["python", "aws"])
        assert score == 100.0


class TestExperienceFit:
    def test_in_range(self):
        assert _experience_fit(2, 5, 3.0) == 100.0

    def test_underqualified_penalty(self):
        score = _experience_fit(5, 10, 2.0)
        assert score < 100.0
        assert score >= 0.0

    def test_overqualified_gentle_penalty(self):
        score = _experience_fit(0, 3, 10.0)
        assert score >= 60.0  # overqualified should still be viable

    def test_no_requirement(self):
        assert _experience_fit(None, None, 5.0) == 100.0

    def test_unknown_candidate_experience(self):
        assert _experience_fit(2, 5, None) == 50.0


class TestSalaryFit:
    def test_within_budget(self):
        assert _salary_fit(100_000.0, 80_000.0) == 100.0

    def test_exact_match(self):
        assert _salary_fit(100_000.0, 100_000.0) == 100.0

    def test_over_budget(self):
        score = _salary_fit(100_000.0, 150_000.0)
        assert score < 100.0
        assert score >= 0.0

    def test_unknown(self):
        assert _salary_fit(None, 80_000.0) == 75.0


class TestLocationFit:
    def test_exact_match(self):
        assert _location_fit("New York", "New York, NY") == 100.0

    def test_remote(self):
        score = _location_fit("Remote", "New York")
        assert score >= 80.0

    def test_different_cities(self):
        assert _location_fit("New York", "San Francisco") == 40.0

    def test_unknown(self):
        assert _location_fit(None, "New York") == 75.0


class TestComputeMatchScore:
    def test_perfect_candidate(self):
        job = _make_job(
            required_skills=["python", "django"],
            min_experience=2, max_experience=5,
            max_salary=120_000, location="Remote",
        )
        profile = _make_profile(
            skills=["python", "django", "aws"],
            years_experience=3,
            expected_salary=100_000,
            location="Remote",
        )
        score = compute_match_score(job, profile)
        assert score.total >= 80.0
        assert "python" in score.matched_skills
        assert "django" in score.matched_skills
        assert score.missing_skills == []

    def test_no_overlap_candidate(self):
        job = _make_job(required_skills=["java", "spring"])
        profile = _make_profile(skills=["python", "django"])
        score = compute_match_score(job, profile)
        assert score.skill_overlap == 0.0
        assert score.total < 60.0

    def test_score_in_range(self):
        job = _make_job(required_skills=["python"])
        profile = _make_profile(skills=["python"])
        score = compute_match_score(job, profile)
        assert 0.0 <= score.total <= 100.0

    def test_ranking_orders_correctly(self):
        job = _make_job(required_skills=["python", "django", "aws"])
        good = _make_profile(user_id=1, skills=["python", "django", "aws"])
        poor = _make_profile(user_id=2, skills=["java"])
        ranked = rank_candidates(job, [poor, good])
        assert ranked[0].candidate_id == 1  # good should be first
        assert ranked[0].score.total > ranked[1].score.total


# ---------------------------------------------------------------------------
# Integration tests — HTTP endpoints
# ---------------------------------------------------------------------------


async def _register_login(client: AsyncClient, email: str, role: str) -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Test@12345", "role": role})
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Test@12345"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_match_score_returns_for_candidate(client: AsyncClient):
    """Candidate can get their match score for any open job (even with empty profile)."""
    hr_tok = await _register_login(client, "match_hr1@test.com", "HR")
    cand_tok = await _register_login(client, "match_cand1@test.com", "CANDIDATE")

    # Create a job
    job_resp = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={
            "title": "Backend Engineer",
            "description": "Build APIs with Python and FastAPI",
            "required_skills": ["python", "fastapi"],
            "company_name": "TestCo",
        },
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/jobs/{job_id}/match-score",
        headers={"Authorization": f"Bearer {cand_tok}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "matched_skills" in data
    assert "missing_skills" in data
    assert 0 <= data["total"] <= 100


@pytest.mark.asyncio
async def test_match_score_hr_forbidden(client: AsyncClient):
    """HR users cannot call the candidate match-score endpoint."""
    hr_tok = await _register_login(client, "match_hr2@test.com", "HR")
    job_resp = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"title": "Eng", "description": "Build things", "company_name": "Co"},
    )
    job_id = job_resp.json()["id"]
    resp = await client.get(
        f"/api/v1/jobs/{job_id}/match-score",
        headers={"Authorization": f"Bearer {hr_tok}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ranked_candidates_hr_only(client: AsyncClient):
    """Candidate cannot call the ranked-candidates endpoint."""
    cand_tok = await _register_login(client, "rank_cand@test.com", "CANDIDATE")
    resp = await client.get(
        "/api/v1/jobs/1/candidates/ranked",
        headers={"Authorization": f"Bearer {cand_tok}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ranked_candidates_returns_list(client: AsyncClient):
    """HR can retrieve a ranked list (may be empty if no profiles)."""
    hr_tok = await _register_login(client, "rank_hr@test.com", "HR")
    job_resp = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={
            "title": "Data Engineer",
            "description": "Build data pipelines",
            "required_skills": ["python", "spark"],
            "company_name": "DataCo",
        },
    )
    job_id = job_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/jobs/{job_id}/candidates/ranked",
        headers={"Authorization": f"Bearer {hr_tok}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
