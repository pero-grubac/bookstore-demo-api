"""Small JSON cache on top of Redis.

Caching is best-effort: if Redis is not configured or unreachable, every call
degrades to a cache miss and the API keeps working. After an error Redis is
skipped for a short while so requests are not slowed down by timeouts.
"""

import json
import logging
import time
from typing import Any

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.core.config import settings

logger = logging.getLogger(__name__)

RETRY_AFTER_SECONDS = 30

client: redis.Redis | None = (
    redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
        retry=Retry(NoBackoff(), 0),
    )
    if settings.REDIS_URL
    else None
)
_skip_until = 0.0


def _available() -> bool:
    return client is not None and time.monotonic() >= _skip_until


def _failed(operation: str, exc: Exception) -> None:
    global _skip_until
    _skip_until = time.monotonic() + RETRY_AFTER_SECONDS
    logger.warning("Redis %s failed, caching paused: %s", operation, exc)


def get(key: str) -> Any | None:
    if not _available():
        return None
    try:
        raw = client.get(key)
    except redis.RedisError as exc:
        _failed("GET", exc)
        return None
    return json.loads(raw) if raw else None


def set(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
    if not _available():
        return
    try:
        client.set(key, json.dumps(value), ex=ttl)
    except redis.RedisError as exc:
        _failed("SET", exc)


def delete(*keys: str) -> None:
    if not keys or not _available():
        return
    try:
        client.delete(*keys)
    except redis.RedisError as exc:
        _failed("DELETE", exc)


def ping() -> bool:
    if client is None:
        return False
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False
