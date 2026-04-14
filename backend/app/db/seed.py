"""
Idempotent seed script.
Run with: python -m app.db.seed
Creates test users if they don't already exist.
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed() -> None:
    """Placeholder — full seed logic added in step 2 (auth feature)."""
    logger.info("Seed script running (scaffold stub — nothing to seed yet)")


if __name__ == "__main__":
    asyncio.run(seed())
