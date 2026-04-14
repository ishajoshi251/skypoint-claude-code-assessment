# Import all models here so Alembic autogenerate and Base.metadata can see them
from app.models.application import Application, ApplicationStatus  # noqa: F401
from app.models.candidate_profile import CandidateProfile  # noqa: F401
from app.models.company import Company  # noqa: F401
from app.models.job import EmploymentType, Job, JobStatus  # noqa: F401
from app.models.resume import Resume  # noqa: F401
from app.models.user import Role, User  # noqa: F401
