from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import (
    ConnectionFailure,
    DuplicateKeyError,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)

from app.core.config import settings


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        status_code: int = 500,
        *,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        self.headers = headers or {}
        super().__init__(message)


class RateLimitExceededError(AppError):
    def __init__(self, retry_after_seconds: int = 60) -> None:
        super().__init__(
            message="Too many requests. Please try again shortly.",
            code="rate_limit_exceeded",
            status_code=429,
            headers={"Retry-After": str(retry_after_seconds)},
        )
        self.retry_after_seconds = retry_after_seconds


def build_error_response(
    *,
    code: str,
    message: str,
    status_code: int,
    details: Any | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


def _validation_message(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "Invalid request."

    first = errors[0]
    loc_parts = [str(part) for part in first.get("loc", []) if part not in {"body", "query"}]
    field = " ".join(loc_parts) if loc_parts else "request"
    msg = str(first.get("msg", "Invalid value."))
    return f"{field}: {msg}"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        response = build_error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details if settings.debug else None,
        )
        for key, value in exc.headers.items():
            response.headers[key] = value
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = list(exc.errors())
        return build_error_response(
            code="validation_error",
            message=_validation_message(errors),
            status_code=422,
            details=errors if settings.debug else None,
        )

    @app.exception_handler(DuplicateKeyError)
    async def integrity_error_handler(_: Request, exc: DuplicateKeyError) -> JSONResponse:
        return build_error_response(
            code="database_conflict",
            message="A conflicting update occurred. Please refresh and try again.",
            status_code=409,
            details=str(exc) if settings.debug else None,
        )

    @app.exception_handler(ConnectionFailure)
    @app.exception_handler(ServerSelectionTimeoutError)
    @app.exception_handler(OperationFailure)
    async def operational_error_handler(_: Request, exc: Exception) -> JSONResponse:
        return build_error_response(
            code="database_unavailable",
            message="The service is temporarily unavailable. Please try again shortly.",
            status_code=503,
            details=str(exc) if settings.debug else None,
        )

    @app.exception_handler(PyMongoError)
    async def database_error_handler(_: Request, exc: PyMongoError) -> JSONResponse:
        return build_error_response(
            code="database_error",
            message="A database error occurred. Please try again.",
            status_code=500,
            details=str(exc) if settings.debug else None,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        return build_error_response(
            code="internal_error",
            message="An unexpected error occurred.",
            status_code=500,
            details=str(exc) if settings.debug else None,
        )
