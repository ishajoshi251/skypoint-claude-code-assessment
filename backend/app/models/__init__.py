# Import all models here so Alembic autogenerate and Base.metadata can see them
from app.models.candidate_profile import CandidateProfile  # noqa: F401
from app.models.user import Role, User  # noqa: F401
