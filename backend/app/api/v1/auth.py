from fastapi import APIRouter, Depends

from app.api.deps import AsyncSessionDep, CurrentUserDep
from app.core.rate_limit import rate_limit_auth
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, MessageResponse, SignupRequest
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)])
async def signup(body: SignupRequest, session: AsyncSessionDep) -> AuthResponse:
    service = AuthService(session)
    result = await service.signup(body)
    return AuthResponse.model_validate(result)


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)])
async def login(body: LoginRequest, session: AsyncSessionDep) -> AuthResponse:
    service = AuthService(session)
    result = await service.login(body)
    return AuthResponse.model_validate(result)


@router.post("/logout", response_model=MessageResponse)
async def logout(_: CurrentUserDep) -> MessageResponse:
    # JWT access tokens are stateless; clients discard the token on logout.
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user)
