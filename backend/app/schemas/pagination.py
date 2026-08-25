"""Shared pagination query parameters."""

from fastapi import Query

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100


def pagination_params(
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0),
) -> tuple[int, int]:
    return limit, offset
