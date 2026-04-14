"""
Auth service — pure business logic, no FastAPI imports.
"""
import structlog
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    REFRESH_TOKEN_TTL_SECONDS,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_token,
    is_valid_token_type,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut

logger = structlog.get_logger(__name__)

_REFRESH_KEY_PREFIX = "refresh_token:"


def _redis_key(jti: str) -> str:
    return f"{_REFRESH_KEY_PREFIX}{jti}"


class AuthService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._db = db
        self._redis = redis

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def register_full(self, req: RegisterRequest) -> tuple[TokenResponse, str]:
        """Create user and return (TokenResponse, raw_refresh_token)."""
        existing = await self._db.execute(select(User).where(User.email == req.email))
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("An account with this email already exists.")

        user = User(
            email=req.email,
            password_hash=hash_password(req.password),
            role=req.role,
            is_active=True,
        )
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)

        logger.info("User registered", user_id=user.id, role=user.role)
        return await self._issue_tokens(user)

    async def login_full(self, email: str, password: str) -> tuple[TokenResponse, str]:
        """Authenticate and return (TokenResponse, raw_refresh_token)."""
        result = await self._db.execute(select(User).where(User.email == email))
        user: User | None = result.scalar_one_or_none()

        # Always call verify_password to avoid timing-based user enumeration
        _DUMMY_HASH = "$2b$12$KIXwm9FVhWCF5a5b1m6uM.B85CmT4BzFzYXHOFEYmCpvXJJ.M/Riy"
        pw_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)

        if not user or not user.is_active or not pw_ok:
            raise UnauthorizedError("Invalid credentials.")

        logger.info("User logged in", user_id=user.id)
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Rotate refresh token. Returns (new_access_token, new_refresh_token)."""
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("Invalid or expired refresh token.")

        if not is_valid_token_type(payload, "refresh"):
            raise UnauthorizedError("Invalid token type.")

        jti: str = payload.get("jti", "")
        user_id_str: str = payload.get("sub", "")

        stored = await self._redis.get(_redis_key(jti))
        if stored is None:
            raise UnauthorizedError("Refresh token has been revoked or expired.")

        result = await self._db.execute(select(User).where(User.id == int(user_id_str)))
        user: User | None = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise UnauthorizedError("Invalid credentials.")

        # Rotate: delete old, issue new
        await self._redis.delete(_redis_key(jti))
        new_access = create_access_token(user.id, user.role.value)
        new_refresh_str, new_jti = create_refresh_token(user.id)
        await self._store_refresh(new_jti, str(user.id))

        logger.info("Refresh token rotated", user_id=user.id)
        return new_access, new_refresh_str

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token from Redis."""
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti", "")
            if jti:
                await self._redis.delete(_redis_key(jti))
        except JWTError:
            pass  # already invalid — no-op

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _issue_tokens(self, user: User) -> tuple[TokenResponse, str]:
        """Create access + refresh tokens, store refresh in Redis."""
        access_token = create_access_token(user.id, user.role.value)
        raw_refresh, jti = create_refresh_token(user.id)
        await self._store_refresh(jti, str(user.id))
        token_resp = TokenResponse(
            access_token=access_token,
            user=UserOut.model_validate(user),
        )
        return token_resp, raw_refresh

    async def _store_refresh(self, jti: str, user_id: str) -> None:
        await self._redis.setex(_redis_key(jti), REFRESH_TOKEN_TTL_SECONDS, user_id)
