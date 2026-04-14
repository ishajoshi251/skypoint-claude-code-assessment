from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, get_redis
from app.core.exceptions import UnauthorizedError
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,   # flip to True behind HTTPS in production
        max_age=7 * 24 * 3600,
        path=_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path=_COOKIE_PATH)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    svc = AuthService(db, redis)
    token_resp, raw_refresh = await svc.register_full(body)
    _set_refresh_cookie(response, raw_refresh)
    return token_resp


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    svc = AuthService(db, redis)
    token_resp, raw_refresh = await svc.login_full(body.email, body.password)
    _set_refresh_cookie(response, raw_refresh)
    return token_resp


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if not refresh_token:
        raise UnauthorizedError("No refresh token provided.")
    svc = AuthService(db, redis)
    new_access, new_refresh = await svc.refresh(refresh_token)
    _set_refresh_cookie(response, new_refresh)
    return RefreshResponse(access_token=new_access)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    svc = AuthService(db, redis)
    if refresh_token:
        await svc.logout(refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserOut.model_validate(current_user)
