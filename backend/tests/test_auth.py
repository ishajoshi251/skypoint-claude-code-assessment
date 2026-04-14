"""
Auth endpoint tests:
- Register (success, duplicate, weak password)
- Login (success, wrong password, unknown user)
- Refresh (valid, revoked/missing cookie)
- Logout
- /me requires auth
"""
import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"

VALID_CANDIDATE = {"email": "alice@example.com", "password": "Alice@123", "role": "CANDIDATE"}
VALID_HR = {"email": "bob@example.com", "password": "Bob@1234", "role": "HR"}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_candidate_success(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json=VALID_CANDIDATE)
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == VALID_CANDIDATE["email"]
    assert body["user"]["role"] == "CANDIDATE"
    # refresh cookie must be set
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_register_hr_success(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json=VALID_HR)
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "HR"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_CANDIDATE)
    resp = await client.post(REGISTER_URL, json=VALID_CANDIDATE)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    resp = await client.post(
        REGISTER_URL, json={"email": "weak@example.com", "password": "weakpwd", "role": "CANDIDATE"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post(
        REGISTER_URL, json={"email": "not-an-email", "password": "Valid@123", "role": "CANDIDATE"}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_CANDIDATE)
    resp = await client.post(LOGIN_URL, json={"email": VALID_CANDIDATE["email"], "password": VALID_CANDIDATE["password"]})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_CANDIDATE)
    resp = await client.post(LOGIN_URL, json={"email": VALID_CANDIDATE["email"], "password": "Wrong@999"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials."


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(LOGIN_URL, json={"email": "ghost@example.com", "password": "Ghost@123"})
    assert resp.status_code == 401
    # Must NOT reveal whether email exists
    assert "Invalid credentials" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_CANDIDATE)
    login_resp = await client.post(LOGIN_URL, json={"email": VALID_CANDIDATE["email"], "password": VALID_CANDIDATE["password"]})
    refresh_token = login_resp.cookies["refresh_token"]

    resp = await client.post(REFRESH_URL, cookies={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    # New refresh cookie should be set (token rotation)
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_refresh_missing_cookie(client: AsyncClient):
    resp = await client.post(REFRESH_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get(ME_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(client: AsyncClient):
    reg = await client.post(REGISTER_URL, json=VALID_HR)
    token = reg.json()["access_token"]
    resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "HR"


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_CANDIDATE)
    login_resp = await client.post(LOGIN_URL, json={"email": VALID_CANDIDATE["email"], "password": VALID_CANDIDATE["password"]})
    token = login_resp.json()["access_token"]
    refresh_token = login_resp.cookies["refresh_token"]

    # Logout
    logout_resp = await client.post(
        LOGOUT_URL,
        headers={"Authorization": f"Bearer {token}"},
        cookies={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200

    # Using old refresh token should now fail
    resp = await client.post(REFRESH_URL, cookies={"refresh_token": refresh_token})
    assert resp.status_code == 401
