"""MongoDB (Motor + Beanie) connection and session token."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import Field

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_initialized = False


class MongoDocument(Document):
    """Shared document base: UUID primary key and timestamps."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)  # type: ignore[assignment]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        use_state_management = True

    async def save(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        self.updated_at = datetime.now(UTC)
        return await super().save(*args, **kwargs)


class MongoSession:
    """Compatibility token for former SQLAlchemy sessions.

    Beanie writes persist immediately. flush/commit/rollback are no-ops so
    existing service and test call sites keep working. `add()` queues documents
    and `flush()` inserts them (mirrors SQLAlchemy test helpers).
    """

    def __init__(self) -> None:
        self._pending: list[MongoDocument] = []

    def add(self, instance: MongoDocument) -> None:
        self._pending.append(instance)

    async def flush(self) -> None:
        pending = list(self._pending)
        self._pending.clear()
        for instance in pending:
            if getattr(instance, "id", None) and await type(instance).get(instance.id):
                await instance.save()
            else:
                await instance.insert()

    async def commit(self) -> None:
        await self.flush()

    async def rollback(self) -> None:
        self._pending.clear()

    async def get(self, model: type[MongoDocument], entity_id: uuid.UUID) -> MongoDocument | None:
        return await model.get(entity_id)


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.resolved_mongodb_url,
            serverSelectionTimeoutMS=5000,
        )
    return _client


def get_database():
    return get_mongo_client()[settings.mongodb_db]


async def init_db() -> None:
    global _initialized
    from app.models import ALL_DOCUMENTS

    await init_beanie(database=get_database(), document_models=ALL_DOCUMENTS)
    _initialized = True


async def ensure_db_initialized() -> None:
    """Initialize Beanie once; raise a clear API error if MongoDB is unavailable."""
    global _initialized
    if _initialized:
        return

    from app.core.exceptions import AppError

    try:
        await init_db()
    except Exception as exc:
        logger.exception("MongoDB initialization failed")
        raise AppError(
            "The service is temporarily unavailable. Please try again shortly.",
            code="database_unavailable",
            status_code=503,
        ) from exc


async def close_db() -> None:
    global _client, _initialized
    if _client is not None:
        _client.close()
        _client = None
    _initialized = False


async def get_async_session() -> AsyncGenerator[MongoSession, None]:
    yield MongoSession()
