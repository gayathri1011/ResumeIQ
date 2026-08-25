from __future__ import annotations

from pymongo import IndexModel

from app.core.database import MongoDocument


class User(MongoDocument):
    email: str
    password_hash: str
    full_name: str | None = None

    class Settings:
        name = "users"
        indexes = [IndexModel([("email", 1)], unique=True)]

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
