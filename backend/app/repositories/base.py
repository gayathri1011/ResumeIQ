import inspect
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, Generic, TypeVar

from pymongo.errors import DuplicateKeyError

from app.core.database import MongoDocument, MongoSession, ensure_db_initialized
from app.core.exceptions import AppError

ModelT = TypeVar("ModelT", bound=MongoDocument)


class BaseRepository(Generic[ModelT]):
    """Generic async CRUD repository over Beanie documents."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for name, member in list(cls.__dict__.items()):
            if name.startswith("_"):
                continue
            if callable(member) and inspect.iscoroutinefunction(member):
                setattr(cls, name, cls._with_db(member))

    def __init__(self, session: MongoSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    @staticmethod
    def _with_db(method: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(method)
        async def wrapper(self: "BaseRepository[Any]", *args: Any, **kwargs: Any) -> Any:
            await self._ensure_db()
            return await method(self, *args, **kwargs)

        return wrapper

    async def _ensure_db(self) -> None:
        await ensure_db_initialized()

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model(**kwargs)
        try:
            await instance.insert()
        except DuplicateKeyError as exc:
            raise AppError(
                "A conflicting update occurred. Please refresh and try again.",
                code="database_conflict",
                status_code=409,
            ) from exc
        return instance

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.model.get(entity_id)

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        **filters: Any,
    ) -> list[ModelT]:
        criteria = []
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                criteria.append(getattr(self.model, key) == value)
        query = self.model.find(*criteria) if criteria else self.model.find()
        return await query.skip(skip).limit(limit).to_list()

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        for key, value in kwargs.items():
            if value is not None and hasattr(instance, key):
                setattr(instance, key, value)
        await instance.save()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await instance.delete()
