from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Cookie, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token, is_valid_token_type
from app.db.session import get_async_session
from app.models.user import Role, User

settings = get_settings()

_bearer = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


# ---------------------------------------------------------------------------
# Redis dependency
# ---------------------------------------------------------------------------

_redis_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding="utf-8",
        )
    return _redis_pool


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------


async def _get_user_from_token(token: str, db: AsyncSession) -> User:
    """Decode access token and return the matching active User."""
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Could not validate credentials.")

    if not is_valid_token_type(payload, "access"):
        raise UnauthorizedError("Invalid token type.")

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Could not validate credentials.")

    result = await db.execute(select(User).where(User.id == int(user_id_str)))
    user: User | None = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("Could not validate credentials.")

    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated.")
    return await _get_user_from_token(credentials.credentials, db)


# ---------------------------------------------------------------------------
# RBAC dependency factory
# ---------------------------------------------------------------------------


def require_role(*roles: Role):
    """Usage: Depends(require_role(Role.HR))"""

    async def _check(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise ForbiddenError()
        return current_user

    return _check
