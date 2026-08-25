from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import MongoSession, get_async_session
from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

AsyncSessionDep = Annotated[MongoSession, Depends(get_async_session)]


async def require_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> HTTPAuthorizationCredentials:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            "Authentication required.",
            code="unauthorized",
            status_code=401,
        )
    return credentials


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(require_bearer_token)],
    session: AsyncSessionDep,
) -> User:
    user_id = decode_access_token(credentials.credentials)
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise AppError(
            "Authentication required.",
            code="unauthorized",
            status_code=401,
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
