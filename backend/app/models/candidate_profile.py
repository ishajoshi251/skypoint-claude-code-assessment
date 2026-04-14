"""
CandidateProfile — full model with all profile fields.
"""
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Core profile fields
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Experience & compensation
    years_experience: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    current_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Skills array
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Latest resume FK (nullable — profile can exist before resume upload)
    resume_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="candidate_profile"
    )

    def __repr__(self) -> str:
        return f"<CandidateProfile user_id={self.user_id}>"
