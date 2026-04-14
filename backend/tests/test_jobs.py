"""
Jobs + Applications CRUD tests:
- HR can create/update/delete jobs
- Candidate cannot create jobs (403)
- Any authenticated user can list/get jobs
- Candidate can apply; duplicate returns 409
- HR can view and update application status
- Object-level authz: HR cannot modify another HR's job
"""
import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
JOBS_URL = "/api/v1/jobs"
APPLICATIONS_URL = "/api/v1/applications"

HR1 = {"email": "hr1_jobs@example.com", "password": "Hr1@12345", "role": "HR"}
HR2 = {"email": "hr2_jobs@example.com", "password": "Hr2@12345", "role": "HR"}
CANDIDATE = {"email": "cand_jobs@example.com", "password": "Cand@1234", "role": "CANDIDATE"}

JOB_PAYLOAD = {
    "title": "Senior Python Engineer",
    "description": "We need an experienced Python engineer to build amazing things.",
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
    "min_experience": 3,
    "max_experience": 8,
    "location": "Remote",
    "employment_type": "FULL_TIME",
    "company_name": "Acme Corp",
}


async def _token(client: AsyncClient, spec: dict) -> str:
    resp = await client.post(REGISTER_URL, json=spec)
    assert resp.status_code == 201
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hr_can_create_job(client: AsyncClient):
    token = await _token(client, HR1)
    resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == JOB_PAYLOAD["title"]
    assert body["company"]["name"] == "Acme Corp"
    assert body["status"] == "OPEN"


@pytest.mark.asyncio
async def test_candidate_cannot_create_job(client: AsyncClient):
    token = await _token(client, CANDIDATE)
    resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_create_job(client: AsyncClient):
    resp = await client.post(JOBS_URL, json=JOB_PAYLOAD)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient):
    hr_token = await _token(client, HR1)
    await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))

    cand_token = await _token(client, CANDIDATE)
    resp = await client.get(JOBS_URL, headers=_auth(cand_token))
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_job_by_id(client: AsyncClient):
    hr_token = await _token(client, HR1)
    create_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = create_resp.json()["id"]

    cand_token = await _token(client, CANDIDATE)
    resp = await client.get(f"{JOBS_URL}/{job_id}", headers=_auth(cand_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


@pytest.mark.asyncio
async def test_get_nonexistent_job_returns_404(client: AsyncClient):
    token = await _token(client, CANDIDATE)
    resp = await client.get(f"{JOBS_URL}/999999", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hr_can_update_own_job(client: AsyncClient):
    hr_token = await _token(client, HR1)
    create_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = create_resp.json()["id"]

    resp = await client.patch(
        f"{JOBS_URL}/{job_id}",
        json={"title": "Lead Python Engineer", "status": "CLOSED"},
        headers=_auth(hr_token),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Lead Python Engineer"
    assert resp.json()["status"] == "CLOSED"


@pytest.mark.asyncio
async def test_hr_cannot_update_another_hrs_job(client: AsyncClient):
    hr1_token = await _token(client, HR1)
    hr2_token = await _token(client, HR2)

    create_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr1_token))
    job_id = create_resp.json()["id"]

    resp = await client.patch(
        f"{JOBS_URL}/{job_id}", json={"title": "Hijacked"}, headers=_auth(hr2_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_hr_can_delete_own_job(client: AsyncClient):
    hr_token = await _token(client, HR1)
    create_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = create_resp.json()["id"]

    resp = await client.delete(f"{JOBS_URL}/{job_id}", headers=_auth(hr_token))
    assert resp.status_code == 204

    get_resp = await client.get(f"{JOBS_URL}/{job_id}", headers=_auth(hr_token))
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_candidate_can_apply(client: AsyncClient):
    hr_token = await _token(client, HR1)
    job_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = job_resp.json()["id"]

    cand_token = await _token(client, CANDIDATE)
    resp = await client.post(
        APPLICATIONS_URL,
        json={"job_id": job_id, "cover_letter": "I am a great fit!"},
        headers=_auth(cand_token),
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "APPLIED"


@pytest.mark.asyncio
async def test_duplicate_application_returns_409(client: AsyncClient):
    hr_token = await _token(client, HR1)
    job_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = job_resp.json()["id"]

    cand_token = await _token(client, CANDIDATE)
    payload = {"job_id": job_id}
    await client.post(APPLICATIONS_URL, json=payload, headers=_auth(cand_token))
    resp = await client.post(APPLICATIONS_URL, json=payload, headers=_auth(cand_token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_hr_cannot_apply(client: AsyncClient):
    hr_token = await _token(client, HR1)
    job_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = job_resp.json()["id"]

    resp = await client.post(
        APPLICATIONS_URL, json={"job_id": job_id}, headers=_auth(hr_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_candidate_can_view_own_applications(client: AsyncClient):
    hr_token = await _token(client, HR1)
    job_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = job_resp.json()["id"]

    cand_token = await _token(client, CANDIDATE)
    await client.post(APPLICATIONS_URL, json={"job_id": job_id}, headers=_auth(cand_token))

    resp = await client.get(f"{APPLICATIONS_URL}/me", headers=_auth(cand_token))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_hr_can_update_application_status(client: AsyncClient):
    hr_token = await _token(client, HR1)
    job_resp = await client.post(JOBS_URL, json=JOB_PAYLOAD, headers=_auth(hr_token))
    job_id = job_resp.json()["id"]

    cand_token = await _token(client, CANDIDATE)
    app_resp = await client.post(
        APPLICATIONS_URL, json={"job_id": job_id}, headers=_auth(cand_token)
    )
    app_id = app_resp.json()["id"]

    resp = await client.patch(
        f"{APPLICATIONS_URL}/{app_id}/status",
        json={"status": "SHORTLISTED"},
        headers=_auth(hr_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SHORTLISTED"
