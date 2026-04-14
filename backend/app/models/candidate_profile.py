"""
CandidateProfile model stub — full columns added in the jobs/applications step.
Defined here so the User.candidate_profile relationship resolves at startup.
"""
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="candidate_profile"
    )

    def __repr__(self) -> str:
        return f"<CandidateProfile user_id={self.user_id}>"
