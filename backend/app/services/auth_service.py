"""Authentication workflows."""

from __future__ import annotations

from app.core.database import MongoSession

from app.core.exceptions import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest


class AuthService:
    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def signup(self, body: SignupRequest) -> dict:
        existing = await self.user_repo.get_by_email(body.email.lower())
        if existing is not None:
            raise AppError(
                "An account with this email already exists.",
                code="email_already_registered",
                status_code=409,
            )

        user = await self.user_repo.create(
            email=body.email.lower(),
            password_hash=hash_password(body.password),
            full_name=body.full_name,
        )
        token, expires_in = create_access_token(user.id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": user,
        }

    async def login(self, body: LoginRequest) -> dict:
        user = await self.user_repo.get_by_email(body.email.lower())
        if user is None or not verify_password(body.password, user.password_hash):
            raise AppError(
                "Invalid email or password.",
                code="invalid_credentials",
                status_code=401,
            )

        token, expires_in = create_access_token(user.id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": user,
        }
