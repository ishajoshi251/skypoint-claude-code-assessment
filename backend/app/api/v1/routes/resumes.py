"""
Resume upload and profile management endpoints.

POST   /resumes/upload            — Candidate uploads PDF/DOCX; auto-parses + updates profile
GET    /resumes/me                — Candidate's own resume list
GET    /resumes/{resume_id}       — Get resume detail (own only)
PUT    /profile/me                — Candidate updates their own profile fields
GET    /profile/me                — Candidate reads their own profile
"""
import mimetypes
import os
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_db, require_role
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.candidate_profile import CandidateProfile
from app.models.resume import Resume
from app.models.user import Role, User
from app.schemas.resumes import CandidateProfileOut, CandidateProfileUpdate, ResumeDetailOut, ResumeOut
from app.services.resume_parser import parse_resume

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["resumes"])
settings = get_settings()

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
_MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_or_create_profile(db: AsyncSession, user_id: int) -> CandidateProfile:
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = CandidateProfile(user_id=user_id)
        db.add(profile)
        await db.flush()  # get profile.id without committing
    return profile


def _detect_mime(file: UploadFile) -> str:
    """Prefer Content-Type header, but sniff from filename as fallback."""
    ct = file.content_type or ""
    if ct in _ALLOWED_MIME_TYPES:
        return ct
    # Sniff from filename
    guessed, _ = mimetypes.guess_type(file.filename or "")
    return guessed or ct


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post("/resumes/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> ResumeOut:
    """Upload a PDF or DOCX resume. Parses it and auto-updates the candidate profile."""
    mime_type = _detect_mime(file)
    if mime_type not in _ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported file type '{mime_type}'. Upload a PDF or DOCX."
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_BYTES:
        raise ValidationError(
            f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # Validate extension matches MIME (basic security check)
    filename = file.filename or "resume"
    ext = os.path.splitext(filename)[1].lower()
    expected_ext = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
    }.get(mime_type, "")
    if ext not in (expected_ext, ""):
        raise ValidationError("File extension does not match content type.")

    # Store file outside webroot on the resumes volume
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Parse
    parsed = parse_resume(file_bytes, mime_type)

    # Persist resume record
    resume = Resume(
        candidate_id=current_user.id,
        file_path=file_path,
        original_filename=filename,
        mime_type=mime_type,
        parsed_text=parsed.text or None,
        parsed_skills=parsed.skills or None,
        parsed_experience_years=parsed.experience_years,
    )
    db.add(resume)
    await db.flush()  # get resume.id

    # Update candidate profile
    profile = await _get_or_create_profile(db, current_user.id)
    profile.resume_id = resume.id
    # Only overwrite skills/experience if we extracted something useful
    if parsed.skills:
        existing = set(profile.skills or [])
        profile.skills = sorted(existing | set(parsed.skills))
    if parsed.experience_years is not None and profile.years_experience is None:
        profile.years_experience = parsed.experience_years

    await db.commit()
    await db.refresh(resume)

    logger.info("Resume uploaded", resume_id=resume.id, user_id=current_user.id)
    return ResumeOut.model_validate(resume)


# ---------------------------------------------------------------------------
# Read own resumes
# ---------------------------------------------------------------------------


@router.get("/resumes/me", response_model=list[ResumeOut])
async def list_my_resumes(
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ResumeOut]:
    result = await db.execute(
        select(Resume)
        .where(Resume.candidate_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    return [ResumeOut.model_validate(r) for r in resumes]


@router.get("/resumes/{resume_id}", response_model=ResumeDetailOut)
async def get_resume(
    resume_id: int,
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeDetailOut:
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume: Resume | None = result.scalar_one_or_none()
    if resume is None:
        raise NotFoundError("Resume")
    if resume.candidate_id != current_user.id:
        raise ForbiddenError()
    return ResumeDetailOut.model_validate(resume)


# ---------------------------------------------------------------------------
# Candidate profile
# ---------------------------------------------------------------------------


@router.get("/profile/me", response_model=CandidateProfileOut)
async def get_my_profile(
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateProfileOut:
    profile = await _get_or_create_profile(db, current_user.id)
    await db.commit()
    return CandidateProfileOut.model_validate(profile)


@router.put("/profile/me", response_model=CandidateProfileOut)
async def update_my_profile(
    body: CandidateProfileUpdate,
    current_user: Annotated[User, Depends(require_role(Role.CANDIDATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateProfileOut:
    profile = await _get_or_create_profile(db, current_user.id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return CandidateProfileOut.model_validate(profile)
