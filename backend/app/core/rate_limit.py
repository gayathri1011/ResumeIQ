"""Simple in-memory rate limiting for sensitive endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_rate_limit(scope: str, request: Request, *, limit: int, window_seconds: int) -> None:
    key = f"{scope}:{_client_key(request)}"
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise RateLimitExceededError(retry_after_seconds=window_seconds)
        bucket.append(now)


async def rate_limit_auth(request: Request) -> None:
    _check_rate_limit(
        "auth",
        request,
        limit=settings.auth_rate_limit_per_minute,
        window_seconds=60,
    )


async def rate_limit_ai(request: Request) -> None:
    _check_rate_limit(
        "ai",
        request,
        limit=settings.ai_rate_limit_per_minute,
        window_seconds=60,
    )
