"""
Idempotent seed script.
Run with: python -m app.db.seed
Uses INSERT … ON CONFLICT DO NOTHING pattern via SQLAlchemy merge.
Safe to re-run on every container start.
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import Role, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

SEED_USERS = [
    {"email": settings.SEED_HR_EMAIL, "password": settings.SEED_HR_PASSWORD, "role": Role.HR},
    {
        "email": settings.SEED_CANDIDATE_EMAIL,
        "password": settings.SEED_CANDIDATE_PASSWORD,
        "role": Role.CANDIDATE,
    },
]


async def _seed_users(session: AsyncSession) -> None:
    for spec in SEED_USERS:
        result = await session.execute(select(User).where(User.email == spec["email"]))
        user: User | None = result.scalar_one_or_none()
        if user is None:
            session.add(
                User(
                    email=spec["email"],
                    password_hash=hash_password(spec["password"]),
                    role=spec["role"],
                    is_active=True,
                )
            )
            logger.info("Seeded user: %s (%s)", spec["email"], spec["role"].value)
        else:
            logger.info("User already exists, skipping: %s", spec["email"])

    await session.commit()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        await _seed_users(session)
    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
