"""
Tests for resume upload + parser, and candidate profile endpoints.
"""
import io
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.services.resume_parser import ParsedResume

# ---------------------------------------------------------------------------
# Minimal PDF and DOCX fixtures for testing (real binary content)
# ---------------------------------------------------------------------------

# Tiny valid PDF that pdfplumber can open
_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
    b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 60 >>\nstream\n"
    b"BT /F1 12 Tf 100 700 Td (Python Django React 2019 - 2023) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n"
    b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
    b"0000000266 00000 n \n0000000378 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n457\n%%EOF\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str, role: str) -> str:
    """Register a user and return the access token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test@12345", "role": role},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Test@12345"},
    )
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests: resume upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient):
    token = await _register_and_login(client, "resume_upload@test.com", "CANDIDATE")
    resp = await client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["original_filename"] == "resume.pdf"
    assert data["mime_type"] == "application/pdf"
    assert isinstance(data["parsed_skills"], list)


@pytest.mark.asyncio
async def test_upload_invalid_mime_rejected(client: AsyncClient):
    token = await _register_and_login(client, "resume_bad_mime@test.com", "CANDIDATE")
    resp = await client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("notes.txt", io.BytesIO(b"some text"), "text/plain")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_requires_candidate_role(client: AsyncClient):
    token = await _register_and_login(client, "resume_hr@test.com", "HR")
    resp = await client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: list and get resumes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_my_resumes(client: AsyncClient):
    token = await _register_and_login(client, "resume_list@test.com", "CANDIDATE")
    # Upload two
    for _ in range(2):
        await client.post(
            "/api/v1/resumes/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
        )
    resp = await client.get("/api/v1/resumes/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_resume_detail(client: AsyncClient):
    token = await _register_and_login(client, "resume_detail@test.com", "CANDIDATE")
    upload = await client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
    )
    resume_id = upload.json()["id"]
    resp = await client.get(
        f"/api/v1/resumes/{resume_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    # Detail endpoint exposes parsed_text field
    assert "parsed_text" in resp.json()


@pytest.mark.asyncio
async def test_cannot_access_other_users_resume(client: AsyncClient):
    tok1 = await _register_and_login(client, "resume_owner@test.com", "CANDIDATE")
    tok2 = await _register_and_login(client, "resume_thief@test.com", "CANDIDATE")
    upload = await client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {tok1}"},
        files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
    )
    resume_id = upload.json()["id"]
    resp = await client.get(
        f"/api/v1/resumes/{resume_id}", headers={"Authorization": f"Bearer {tok2}"}
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: candidate profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_profile_creates_if_missing(client: AsyncClient):
    token = await _register_and_login(client, "profile_new@test.com", "CANDIDATE")
    resp = await client.get("/api/v1/profile/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] is None


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    token = await _register_and_login(client, "profile_update@test.com", "CANDIDATE")
    resp = await client.put(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Jane Doe",
            "headline": "Senior Python Developer",
            "skills": ["python", "django", "aws"],
            "years_experience": 5.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Jane Doe"
    assert "python" in data["skills"]
    assert data["years_experience"] == 5.0


@pytest.mark.asyncio
async def test_upload_merges_skills_into_profile(client: AsyncClient):
    token = await _register_and_login(client, "profile_merge@test.com", "CANDIDATE")
    # Pre-set skills
    await client.put(
        "/api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"skills": ["java", "spring"]},
    )
    # Upload resume that will extract python/django/react
    await client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
    )
    resp = await client.get("/api/v1/profile/me", headers={"Authorization": f"Bearer {token}"})
    skills = set(resp.json()["skills"] or [])
    # java and spring should still be there (merge, not replace)
    assert "java" in skills
    assert "spring" in skills


@pytest.mark.asyncio
async def test_upload_updates_profile_with_parsed_resume_basics(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    token = await _register_and_login(client, "profile_autofill@test.com", "CANDIDATE")

    def fake_parse_resume(_file_bytes: bytes, _mime_type: str) -> ParsedResume:
        return ParsedResume(
            text="Devansh Joshi\nBackend Engineer\nLocation: Bengaluru, KA\nPython FastAPI",
            skills=["python", "fastapi"],
            experience_years=3.5,
            full_name="Devansh Joshi",
            headline="Backend Engineer",
            location="Bengaluru, KA",
        )

    async def fake_embed_text(_text: str) -> list[float]:
        return [0.0] * 384

    monkeypatch.setattr("app.api.v1.routes.resumes.parse_resume", fake_parse_resume)
    monkeypatch.setattr("app.api.v1.routes.resumes.embed_text", fake_embed_text)

    upload = await client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    resp = await client.get("/api/v1/profile/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Devansh Joshi"
    assert data["headline"] == "Backend Engineer"
    assert data["location"] == "Bengaluru, KA"
    assert data["years_experience"] == 3.5
    assert set(data["skills"]) >= {"python", "fastapi"}


@pytest.mark.asyncio
async def test_parse_jd_returns_description_for_autofill(client: AsyncClient):
    token = await _register_and_login(client, "jd_parse_hr@test.com", "HR")
    jd_text = (
        "Senior Backend Engineer\n"
        "Location: Remote\n"
        "We need 4-7 years of experience with Python, FastAPI, PostgreSQL, and AWS."
    )
    resp = await client.post(
        "/api/v1/parse/jd",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("jd.txt", io.BytesIO(jd_text.encode()), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == "Senior Backend Engineer"
    assert data["description"] == (
        "Senior Backend Engineer\n"
        "We need 4-7 years of experience with Python, FastAPI, PostgreSQL, and AWS."
    )
    assert data["location"] == "Remote"
    assert data["min_experience"] == 4.0
    assert data["max_experience"] == 7.0
    assert set(data["skills"]) >= {"python", "fastapi", "postgresql", "aws"}


@pytest.mark.asyncio
async def test_parse_labelled_jd_autofills_company_salary_and_skills(client: AsyncClient):
    token = await _register_and_login(client, "jd_labelled_hr@test.com", "HR")
    jd_text = (
        "Company Name: TechNova Solutions Pvt Ltd\n"
        "Role Name: Backend Software Engineer\n"
        "Salary Range: ₹8,00,000 - ₹15,00,000 per annum\n"
        "Location: Pune, India (Hybrid)\n"
        "Skills Required:\n"
        "- Python, AWS Lambda, API Gateway, DynamoDB\n"
        "- REST API Development\n"
    )
    resp = await client.post(
        "/api/v1/parse/jd",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("labelled-jd.txt", io.BytesIO(jd_text.encode()), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["company_name"] == "TechNova Solutions Pvt Ltd"
    assert data["title"] == "Backend Software Engineer"
    assert data["location"] == "Pune, India (Hybrid)"
    assert data["min_salary"] == 800000.0
    assert data["max_salary"] == 1500000.0
    assert "Company Name:" not in data["description"]
    assert set(data["skills"]) >= {
        "python",
        "aws",
        "lambda",
        "api gateway",
        "dynamodb",
        "REST API Development",
    }
