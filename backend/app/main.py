import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import close_db, ensure_db_initialized
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    try:
        await ensure_db_initialized()
    except Exception:
        logger.exception(
            "MongoDB is not available; health checks still work, but data routes will fail until it is up."
        )
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ResumeIQ API",
        description="AI Resume Intelligence & Job Matching Platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
