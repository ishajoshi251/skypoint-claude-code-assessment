"""
Analytics endpoint tests:
- Summary, funnel, skills require HR role (candidates get 403)
- Unauthenticated requests get 401
- Response shapes are correct
- Summary reflects job + application data correctly
"""
import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
JOBS_URL = "/api/v1/jobs"
APPLICATIONS_URL = "/api/v1/applications"
SUMMARY_URL = "/api/v1/analytics/summary"
FUNNEL_URL = "/api/v1/analytics/funnel"
SKILLS_URL = "/api/v1/analytics/skills"

HR = {"email": "analytics_hr@example.com", "password": "Hr@12345", "role": "HR"}
CANDIDATE = {"email": "analytics_cand@example.com", "password": "Cand@1234", "role": "CANDIDATE"}

JOB_PAYLOAD = {
    "title": "ML Engineer",
    "description": "Build machine learning pipelines at scale.",
    "required_skills": ["Python", "PyTorch", "Kubernetes"],
    "company_name": "AICo",
    "min_experience": 2,
    "max_experience": 6,
    "location": "Remote",
    "employment_type": "FULL_TIME",
}


async def _register_and_token(client: AsyncClient, spec: dict) -> str:
    resp = await client.post(REGISTER_URL, json=spec)
    assert resp.status_code == 201
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Access control — all three endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_requires_auth(client: AsyncClient):
    resp = await client.get(SUMMARY_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_funnel_requires_auth(client: AsyncClient):
    resp = await client.get(FUNNEL_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_skills_requires_auth(client: AsyncClient):
    resp = await client.get(SKILLS_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_summary_candidate_forbidden(client: AsyncClient):
    token = await _register_and_token(client, CANDIDATE)
    resp = await client.get(SUMMARY_URL, headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_funnel_candidate_forbidden(client: AsyncClient):
    token = await _register_and_token(client, CANDIDATE)
    resp = await client.get(FUNNEL_URL, headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_skills_candidate_forbidden(client: AsyncClient):
    token = await _register_and_token(client, CANDIDATE)
    resp = await client.get(SKILLS_URL, headers=_auth(token))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Summary — shape and zero-state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_hr_empty(client: AsyncClient):
    """Fresh HR with no jobs returns all zeros."""
    token = await _register_and_token(
        client, {"email": "anly_empty_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    resp = await client.get(SUMMARY_URL, headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_jobs"] == 0
    assert body["open_jobs"] == 0
    assert body["total_applications"] == 0
    assert body["avg_match_score"] is None
    assert body["hired_count"] == 0
    assert body["active_pipeline"] == 0


@pytest.mark.asyncio
async def test_summary_reflects_posted_job(client: AsyncClient):
    """After posting a job, total_jobs and open_jobs increment."""
    hr_token = await _register_and_token(
        client, {"email": "anly_post_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))

    resp = await client.get(SUMMARY_URL, headers=_auth(hr_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_jobs"] >= 1
    assert body["open_jobs"] >= 1


@pytest.mark.asyncio
async def test_summary_counts_application(client: AsyncClient):
    """Applying to an HR's job increments total_applications and active_pipeline."""
    hr_token = await _register_and_token(
        client, {"email": "anly_app_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    cand_token = await _register_and_token(
        client, {"email": "anly_app_cand@example.com", "password": "Cand@1234", "role": "CANDIDATE"}
    )
    job_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = job_resp.json()["id"]

    await client.post(APPLICATIONS_URL, json={"job_id": job_id}, headers=_auth(cand_token))

    resp = await client.get(SUMMARY_URL, headers=_auth(hr_token))
    body = resp.json()
    assert body["total_applications"] >= 1
    assert body["active_pipeline"] >= 1


# ---------------------------------------------------------------------------
# Funnel — shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_funnel_returns_list(client: AsyncClient):
    token = await _register_and_token(
        client, {"email": "anly_funnel_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    resp = await client.get(FUNNEL_URL, headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_funnel_row_shape(client: AsyncClient):
    """Each funnel row has the required fields."""
    hr_token = await _register_and_token(
        client, {"email": "anly_frow_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))

    resp = await client.get(FUNNEL_URL, headers=_auth(hr_token))
    rows = resp.json()
    assert len(rows) >= 1
    row = rows[0]
    for field in ("job_id", "job_title", "company", "status",
                  "applied", "shortlisted", "interview", "offered",
                  "hired", "rejected", "total"):
        assert field in row, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_funnel_counts_application(client: AsyncClient):
    """Applying to a job shows up in the funnel's applied count."""
    hr_token = await _register_and_token(
        client, {"email": "anly_fcnt_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    cand_token = await _register_and_token(
        client, {"email": "anly_fcnt_cand@example.com", "password": "Cand@1234", "role": "CANDIDATE"}
    )
    job_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = job_resp.json()["id"]

    await client.post(APPLICATIONS_URL, json={"job_id": job_id}, headers=_auth(cand_token))

    resp = await client.get(FUNNEL_URL, headers=_auth(hr_token))
    rows = resp.json()
    row = next((r for r in rows if r["job_id"] == job_id), None)
    assert row is not None
    assert row["applied"] >= 1
    assert row["total"] >= 1


# ---------------------------------------------------------------------------
# Skills — shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skills_returns_list(client: AsyncClient):
    token = await _register_and_token(
        client, {"email": "anly_skills_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    resp = await client.get(SKILLS_URL, headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_skills_row_shape(client: AsyncClient):
    """Skills endpoint returns objects with 'skill' and 'count' keys."""
    hr_token = await _register_and_token(
        client, {"email": "anly_srow_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    # Post a job so skills exist
    await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))

    resp = await client.get(SKILLS_URL, headers=_auth(hr_token))
    items = resp.json()
    if items:
        assert "skill" in items[0]
        assert "count" in items[0]
        assert isinstance(items[0]["count"], int)
        assert items[0]["count"] >= 1


@pytest.mark.asyncio
async def test_skills_sorted_descending(client: AsyncClient):
    """Most demanded skills come first."""
    hr_token = await _register_and_token(
        client, {"email": "anly_sort_hr@example.com", "password": "Hr@12345", "role": "HR"}
    )
    # Post two jobs both requiring Python — it should rank at the top
    for i in range(2):
        await client.post(
            JOBS_URL,
            json={**JOB_PAYLOAD, "required_skills": ["Python", f"SkillUnique{i}"]},
            headers=_auth(hr_token),
        )

    resp = await client.get(SKILLS_URL, headers=_auth(hr_token))
    items = resp.json()
    if len(items) >= 2:
        assert items[0]["count"] >= items[1]["count"]
