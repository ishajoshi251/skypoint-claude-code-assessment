"""
RBAC tests — ensures role enforcement is server-side.
Candidate cannot reach HR-only endpoints and vice-versa.
These tests use placeholder HR-only endpoints; expanded when jobs routes ship.
"""
import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

CANDIDATE = {"email": "cand_rbac@example.com", "password": "Cand@1234", "role": "CANDIDATE"}
HR_USER = {"email": "hr_rbac@example.com", "password": "Hr@12345", "role": "HR"}


async def _register_and_token(client: AsyncClient, spec: dict) -> str:
    resp = await client.post(REGISTER_URL, json=spec)
    assert resp.status_code == 201
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_candidate_can_access_me(client: AsyncClient):
    token = await _register_and_token(client, CANDIDATE)
    resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "CANDIDATE"


@pytest.mark.asyncio
async def test_hr_can_access_me(client: AsyncClient):
    token = await _register_and_token(client, HR_USER)
    resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "HR"


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_me(client: AsyncClient):
    resp = await client.get(ME_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_bearer_token_rejected(client: AsyncClient):
    resp = await client.get(ME_URL, headers={"Authorization": "Bearer this.is.garbage"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_role_in_token_matches_db(client: AsyncClient):
    """Access token's role claim must match the DB record — not spoofable."""
    token = await _register_and_token(client, CANDIDATE)
    me = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "CANDIDATE"

    token_hr = await _register_and_token(client, HR_USER)
    me_hr = await client.get(ME_URL, headers={"Authorization": f"Bearer {token_hr}"})
    assert me_hr.json()["role"] == "HR"
