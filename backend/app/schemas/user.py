import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema, TimestampSchema


class UserCreate(BaseSchema):
    email: EmailStr
    password_hash: str = Field(min_length=1, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(BaseSchema):
    email: EmailStr | None = None
    password_hash: str | None = Field(default=None, min_length=1, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)


class UserRead(TimestampSchema):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
