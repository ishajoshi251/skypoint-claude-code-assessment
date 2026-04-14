"""
Tests for HR candidate search endpoints (integration).
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_login(client: AsyncClient, email: str, role: str) -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Test@12345", "role": role})
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Test@12345"})
    return r.json()["access_token"]


async def _create_job(client: AsyncClient, token: str, **kwargs) -> dict:
    defaults = {
        "title": "Backend Engineer",
        "description": "Build APIs with Python and FastAPI",
        "required_skills": ["python", "fastapi"],
        "company_name": "SearchCo",
    }
    defaults.update(kwargs)
    r = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json=defaults,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_requires_hr(client: AsyncClient):
    """Candidates cannot call the smart-search endpoint."""
    cand_tok = await _register_login(client, "srch_cand1@test.com", "CANDIDATE")
    resp = await client.post(
        "/api/v1/candidates/search",
        headers={"Authorization": f"Bearer {cand_tok}"},
        json={"required_skills": ["python"]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_candidates_requires_hr(client: AsyncClient):
    """Candidates cannot list all candidates."""
    cand_tok = await _register_login(client, "srch_cand2@test.com", "CANDIDATE")
    resp = await client.get(
        "/api/v1/candidates",
        headers={"Authorization": f"Bearer {cand_tok}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Smart search validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_requires_at_least_one_filter(client: AsyncClient):
    """Search with no filters returns 422 or 400."""
    hr_tok = await _register_login(client, "srch_hr1@test.com", "HR")
    resp = await client.post(
        "/api/v1/candidates/search",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={},
    )
    # Should fail validation — no query params provided
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_search_by_skills_returns_list(client: AsyncClient):
    """HR can search with required_skills and get a list back (may be empty)."""
    hr_tok = await _register_login(client, "srch_hr2@test.com", "HR")
    resp = await client.post(
        "/api/v1/candidates/search",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"required_skills": ["python", "django"]},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_by_job_id(client: AsyncClient):
    """HR can search using an existing job as the query basis."""
    hr_tok = await _register_login(client, "srch_hr3@test.com", "HR")
    job = await _create_job(client, hr_tok)

    resp = await client.post(
        "/api/v1/candidates/search",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"job_id": job["id"]},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_by_nonexistent_job_returns_404(client: AsyncClient):
    """Search referencing a non-existent job_id returns 404."""
    hr_tok = await _register_login(client, "srch_hr4@test.com", "HR")
    resp = await client.post(
        "/api/v1/candidates/search",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"job_id": 999999},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_with_query_text(client: AsyncClient):
    """HR can search with free-text JD query."""
    hr_tok = await _register_login(client, "srch_hr5@test.com", "HR")

    # Patch embed_text to avoid loading the ML model in unit tests
    with patch("app.api.v1.routes.candidates.embed_text", return_value=[0.1] * 384):
        resp = await client.post(
            "/api/v1/candidates/search",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={
                "query_text": "Senior Python developer with FastAPI and PostgreSQL experience",
                "min_score": 0.0,
            },
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_result_schema(client: AsyncClient):
    """Search results contain expected fields."""
    hr_tok = await _register_login(client, "srch_hr6@test.com", "HR")
    cand_tok = await _register_login(client, "srch_cand6@test.com", "CANDIDATE")

    # Give the candidate a profile
    await client.put(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {cand_tok}"},
        json={"skills": ["python", "fastapi"], "years_experience": 3},
    )

    resp = await client.post(
        "/api/v1/candidates/search",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"required_skills": ["python"]},
    )
    assert resp.status_code == 200
    items = resp.json()
    if items:
        item = items[0]
        assert "candidate_id" in item
        assert "email" in item
        assert "score" in item
        score = item["score"]
        assert "total" in score
        assert "matched_skills" in score
        assert "missing_skills" in score
        assert 0 <= score["total"] <= 100


@pytest.mark.asyncio
async def test_search_min_score_filter(client: AsyncClient):
    """Results with score below min_score are excluded."""
    hr_tok = await _register_login(client, "srch_hr7@test.com", "HR")

    resp = await client.post(
        "/api/v1/candidates/search",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"required_skills": ["python"], "min_score": 95.0},
    )
    assert resp.status_code == 200
    # All returned results must be >= 95
    for item in resp.json():
        assert item["score"]["total"] >= 95.0


@pytest.mark.asyncio
async def test_list_candidates_returns_paginated(client: AsyncClient):
    """HR can list candidates with pagination."""
    hr_tok = await _register_login(client, "list_hr1@test.com", "HR")
    resp = await client.get(
        "/api/v1/candidates?skip=0&limit=5",
        headers={"Authorization": f"Bearer {hr_tok}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_candidate_profile_hr(client: AsyncClient):
    """HR can fetch a single candidate's profile by user_id."""
    hr_tok = await _register_login(client, "get_hr1@test.com", "HR")
    cand_tok = await _register_login(client, "get_cand1@test.com", "CANDIDATE")

    # Update profile so it exists
    await client.put(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {cand_tok}"},
        json={"headline": "Python Dev"},
    )

    # Get candidate user_id via their own profile
    profile_resp = await client.get(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {cand_tok}"},
    )
    cand_profile = profile_resp.json()
    user_id = cand_profile["user_id"]

    resp = await client.get(
        f"/api/v1/candidates/{user_id}",
        headers={"Authorization": f"Bearer {hr_tok}"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == user_id


@pytest.mark.asyncio
async def test_get_nonexistent_candidate_returns_404(client: AsyncClient):
    """Fetching a non-existent candidate profile returns 404."""
    hr_tok = await _register_login(client, "get_hr2@test.com", "HR")
    resp = await client.get(
        "/api/v1/candidates/999999",
        headers={"Authorization": f"Bearer {hr_tok}"},
    )
    assert resp.status_code == 404
