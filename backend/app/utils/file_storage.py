"""File storage abstraction — local disk now, object storage later."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles

from app.core.config import settings


class FileStorage(ABC):
    @abstractmethod
    async def save_resume_file(
        self,
        *,
        content: bytes,
        original_filename: str,
        resume_id: uuid.UUID,
    ) -> str:
        """Persist file bytes and return a storage-relative path."""


class LocalFileStorage(FileStorage):
    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or settings.file_storage_path)

    def _resume_dir(self, resume_id: uuid.UUID) -> Path:
        return self.base_path / "resumes" / str(resume_id)

    async def save_resume_file(
        self,
        *,
        content: bytes,
        original_filename: str,
        resume_id: uuid.UUID,
    ) -> str:
        target_dir = self._resume_dir(resume_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(original_filename).name
        target_path = target_dir / safe_name

        async with aiofiles.open(target_path, "wb") as f:
            await f.write(content)

        return str(target_path.relative_to(self.base_path))


def get_file_storage() -> FileStorage:
    backend = settings.file_storage_backend.lower()
    if backend == "local":
        return LocalFileStorage()
    raise NotImplementedError(f"Storage backend '{backend}' is not implemented yet.")
