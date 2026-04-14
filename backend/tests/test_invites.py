"""
Tests for bulk invite endpoints (integration).
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_login(client: AsyncClient, email: str, role: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test@12345", "role": role},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Test@12345"},
    )
    return r.json()["access_token"]


async def _create_job(client: AsyncClient, token: str) -> dict:
    r = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Python Engineer",
            "description": "Build APIs",
            "required_skills": ["python"],
            "company_name": "InviteCo",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _get_candidate_id(client: AsyncClient, token: str) -> int:
    r = await client.get("/api/v1/profile/me", headers={"Authorization": f"Bearer {token}"})
    return r.json()["user_id"]


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_invite_requires_hr(client: AsyncClient):
    """Candidates cannot send bulk invites."""
    cand_tok = await _register_login(client, "inv_cand_ac@test.com", "CANDIDATE")
    resp = await client.post(
        "/api/v1/invites/bulk",
        headers={"Authorization": f"Bearer {cand_tok}"},
        json={"job_id": 1, "candidate_ids": [1]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_invites_requires_hr(client: AsyncClient):
    """Candidates cannot list HR-sent invites."""
    cand_tok = await _register_login(client, "inv_cand_list@test.com", "CANDIDATE")
    resp = await client.get(
        "/api/v1/invites",
        headers={"Authorization": f"Bearer {cand_tok}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Bulk invite happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_invite_sends_email(client: AsyncClient):
    """HR can send an invite; result includes the invited candidate."""
    hr_tok = await _register_login(client, "inv_hr1@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand1@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        resp = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data["invited"]) == 1
    assert data["skipped"] == []
    invite = data["invited"][0]
    assert invite["candidate_id"] == cand_id
    assert invite["job_id"] == job["id"]
    assert invite["status"] == "SENT"


@pytest.mark.asyncio
async def test_bulk_invite_skips_duplicates(client: AsyncClient):
    """Inviting the same candidate twice skips on the second call."""
    hr_tok = await _register_login(client, "inv_hr2@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand2@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        # First invite
        r1 = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )
        assert r1.status_code == 201

        # Second invite — should be skipped
        r2 = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )

    assert r2.status_code == 201
    data = r2.json()
    assert cand_id in data["skipped"]
    assert data["invited"] == []


@pytest.mark.asyncio
async def test_bulk_invite_nonexistent_job_returns_404(client: AsyncClient):
    """Inviting candidates for a non-existent job returns 404."""
    hr_tok = await _register_login(client, "inv_hr3@test.com", "HR")
    resp = await client.post(
        "/api/v1/invites/bulk",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"job_id": 999999, "candidate_ids": [1]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bulk_invite_forbidden_for_other_hr_job(client: AsyncClient):
    """HR cannot send invites for a job they didn't post."""
    hr1_tok = await _register_login(client, "inv_hr4a@test.com", "HR")
    hr2_tok = await _register_login(client, "inv_hr4b@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand4@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr1_tok)

    resp = await client.post(
        "/api/v1/invites/bulk",
        headers={"Authorization": f"Bearer {hr2_tok}"},
        json={"job_id": job["id"], "candidate_ids": [cand_id]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_bulk_invite_with_custom_message(client: AsyncClient):
    """Custom message is stored on the invite record."""
    hr_tok = await _register_login(client, "inv_hr5@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand5@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)
    msg = "We think you'd be a great fit for our team!"

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        resp = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id], "message": msg},
        )

    assert resp.status_code == 201
    invite = resp.json()["invited"][0]
    assert invite["message"] == msg


# ---------------------------------------------------------------------------
# List invites
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hr_list_invites(client: AsyncClient):
    """HR can list invites they sent."""
    hr_tok = await _register_login(client, "inv_hr6@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand6@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )

    resp = await client.get(
        "/api/v1/invites",
        headers={"Authorization": f"Bearer {hr_tok}"},
    )
    assert resp.status_code == 200
    invites = resp.json()
    assert any(i["candidate_id"] == cand_id for i in invites)


@pytest.mark.asyncio
async def test_candidate_list_received_invites(client: AsyncClient):
    """Candidate can list invites they received."""
    hr_tok = await _register_login(client, "inv_hr7@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand7@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )

    resp = await client.get(
        "/api/v1/invites/received",
        headers={"Authorization": f"Bearer {cand_tok}"},
    )
    assert resp.status_code == 200
    invites = resp.json()
    assert any(i["job_id"] == job["id"] for i in invites)


# ---------------------------------------------------------------------------
# Invite status updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_can_accept_invite(client: AsyncClient):
    """Candidate accepts an invite and status changes to ACCEPTED."""
    hr_tok = await _register_login(client, "inv_hr8@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand8@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        invite_resp = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )
    invite_id = invite_resp.json()["invited"][0]["id"]

    resp = await client.patch(
        f"/api/v1/invites/{invite_id}/status",
        headers={"Authorization": f"Bearer {cand_tok}"},
        json={"status": "ACCEPTED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_candidate_can_decline_invite(client: AsyncClient):
    """Candidate declines an invite and status changes to DECLINED."""
    hr_tok = await _register_login(client, "inv_hr9@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand9@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        invite_resp = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )
    invite_id = invite_resp.json()["invited"][0]["id"]

    resp = await client.patch(
        f"/api/v1/invites/{invite_id}/status",
        headers={"Authorization": f"Bearer {cand_tok}"},
        json={"status": "DECLINED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DECLINED"


@pytest.mark.asyncio
async def test_hr_cannot_update_invite_status(client: AsyncClient):
    """HR cannot use the status-update endpoint (candidate-only)."""
    hr_tok = await _register_login(client, "inv_hr10@test.com", "HR")
    cand_tok = await _register_login(client, "inv_cand10@test.com", "CANDIDATE")
    cand_id = await _get_candidate_id(client, cand_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        invite_resp = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand_id]},
        )
    invite_id = invite_resp.json()["invited"][0]["id"]

    resp = await client.patch(
        f"/api/v1/invites/{invite_id}/status",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"status": "ACCEPTED"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_candidate_cannot_update_other_candidates_invite(client: AsyncClient):
    """Candidate cannot update another candidate's invite status."""
    hr_tok = await _register_login(client, "inv_hr11@test.com", "HR")
    cand1_tok = await _register_login(client, "inv_cand11a@test.com", "CANDIDATE")
    cand2_tok = await _register_login(client, "inv_cand11b@test.com", "CANDIDATE")
    cand1_id = await _get_candidate_id(client, cand1_tok)
    job = await _create_job(client, hr_tok)

    with patch("app.api.v1.routes.invites.send_email", return_value=True):
        invite_resp = await client.post(
            "/api/v1/invites/bulk",
            headers={"Authorization": f"Bearer {hr_tok}"},
            json={"job_id": job["id"], "candidate_ids": [cand1_id]},
        )
    invite_id = invite_resp.json()["invited"][0]["id"]

    # cand2 tries to accept cand1's invite
    resp = await client.patch(
        f"/api/v1/invites/{invite_id}/status",
        headers={"Authorization": f"Bearer {cand2_tok}"},
        json={"status": "ACCEPTED"},
    )
    assert resp.status_code == 403
