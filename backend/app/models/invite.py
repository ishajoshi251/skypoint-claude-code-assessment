import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InviteStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        UniqueConstraint("hr_user_id", "candidate_id", "job_id", name="uq_invite_hr_candidate_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    hr_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus), nullable=False, default=InviteStatus.PENDING
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    hr_user: Mapped["User"] = relationship("User", foreign_keys=[hr_user_id])  # noqa: F821
    candidate: Mapped["User"] = relationship("User", foreign_keys=[candidate_id])  # noqa: F821
    job: Mapped["Job"] = relationship("Job")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Invite id={self.id} job_id={self.job_id} candidate_id={self.candidate_id}>"
