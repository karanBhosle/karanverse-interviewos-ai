from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError, ForbiddenError
from app.models.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: UUID, email: str) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expires}
    return jwt.encode(payload, settings.authentication_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.authentication_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError(401, "unauthorized", "Invalid or expired access token") from exc


LOCAL_USER_EMAIL = "karan@local"
LOCAL_USER_NAME = "Karan"


async def get_or_create_local_user(db: AsyncSession) -> User:
    user = await db.scalar(select(User).where(User.email == LOCAL_USER_EMAIL))
    if user is not None:
        return user
    user = User(
        email=LOCAL_USER_EMAIL,
        hashed_password=hash_password("local-dev-only"),
        display_name=LOCAL_USER_NAME,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    settings = get_settings()
    if authorization and authorization.lower().startswith("bearer "):
        try:
            payload = decode_access_token(authorization.split(" ", 1)[1])
            user = await db.scalar(select(User).where(User.id == UUID(payload["sub"])))
            if user is not None:
                return user
            if settings.auth_required:
                raise AppError(401, "unauthorized", "User no longer exists")
        except AppError:
            if settings.auth_required:
                raise
    elif settings.auth_required:
        raise AppError(401, "unauthorized", "Missing bearer token")
    return await get_or_create_local_user(db)


def assert_owner(resource_user_id: UUID, current_user: User) -> None:
    if resource_user_id != current_user.id:
        raise ForbiddenError()
