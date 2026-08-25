"""Password hashing and JWT utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AppError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def create_access_token(user_id: UUID) -> tuple[str, int]:
    expires_minutes = settings.access_token_expire_minutes
    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_minutes * 60


def decode_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            "Access token has expired. Please log in again.",
            code="token_expired",
            status_code=401,
        ) from exc
    except jwt.PyJWTError as exc:
        raise AppError(
            "Invalid access token.",
            code="invalid_token",
            status_code=401,
        ) from exc

    subject = payload.get("sub")
    token_type = payload.get("type")
    if not subject or token_type != "access":
        raise AppError("Invalid access token.", code="invalid_token", status_code=401)

    try:
        return UUID(str(subject))
    except ValueError as exc:
        raise AppError("Invalid access token.", code="invalid_token", status_code=401) from exc
