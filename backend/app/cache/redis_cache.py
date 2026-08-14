from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.config import settings
from app.monitoring.metrics import metrics


logger = logging.getLogger("library.cache")


class CacheStatus(str, Enum):
    HIT = "HIT"
    MISS = "MISS"
    BYPASS = "BYPASS"


@dataclass(frozen=True)
class CacheLookup:
    value: Any | None
    status: CacheStatus


class RedisCache:
    """Small Redis adapter with graceful database fallback."""

    def __init__(self) -> None:
        self._client: Any | None = None
        self._client_initialized = False

    def set_client(self, client: Any | None) -> None:
        """Inject a Redis-compatible client, primarily for testing."""
        self._client = client
        self._client_initialized = True

    def reset_client(self) -> None:
        self._client = None
        self._client_initialized = False

    def _get_client(self) -> Any | None:
        if self._client_initialized:
            return self._client

        self._client_initialized = True

        try:
            from redis import Redis
        except ImportError:
            logger.warning(
                "cache.redis_package_missing",
                extra={"redis_url": settings.redis_url},
            )
            return None

        self._client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        return self._client

    def get_json(self, key: str) -> CacheLookup:
        client = self._get_client()

        if client is None:
            metrics.record_cache(CacheStatus.BYPASS.value)
            return CacheLookup(None, CacheStatus.BYPASS)

        try:
            cached_value = client.get(key)
        except Exception as error:
            logger.warning(
                "cache.read_failed",
                extra={"cache_key": key, "error": str(error)},
            )
            metrics.record_cache(CacheStatus.BYPASS.value)
            return CacheLookup(None, CacheStatus.BYPASS)

        if cached_value is None:
            metrics.record_cache(CacheStatus.MISS.value)
            logger.debug(
                "cache.miss",
                extra={"cache_key": key},
            )
            return CacheLookup(None, CacheStatus.MISS)

        try:
            value = json.loads(cached_value)
        except (TypeError, json.JSONDecodeError) as error:
            logger.warning(
                "cache.invalid_payload",
                extra={"cache_key": key, "error": str(error)},
            )
            self.delete(key)
            metrics.record_cache(CacheStatus.MISS.value)
            return CacheLookup(None, CacheStatus.MISS)

        metrics.record_cache(CacheStatus.HIT.value)
        logger.debug(
            "cache.hit",
            extra={"cache_key": key},
        )
        return CacheLookup(value, CacheStatus.HIT)

    def set_json(self, key: str, value: Any) -> bool:
        client = self._get_client()

        if client is None:
            return False

        try:
            client.setex(
                key,
                settings.cache_ttl_seconds,
                json.dumps(value, default=str),
            )
        except Exception as error:
            logger.warning(
                "cache.write_failed",
                extra={"cache_key": key, "error": str(error)},
            )
            return False

        logger.debug(
            "cache.value_stored",
            extra={"cache_key": key},
        )
        return True

    def delete(self, *keys: str) -> bool:
        if not keys:
            return True

        client = self._get_client()

        if client is None:
            return False

        try:
            client.delete(*keys)
        except Exception as error:
            logger.warning(
                "cache.delete_failed",
                extra={"cache_keys": list(keys), "error": str(error)},
            )
            return False

        return True

    def delete_pattern(self, pattern: str) -> bool:
        client = self._get_client()

        if client is None:
            return False

        try:
            keys = list(client.scan_iter(match=pattern))
            if keys:
                client.delete(*keys)
        except Exception as error:
            logger.warning(
                "cache.pattern_delete_failed",
                extra={"cache_pattern": pattern, "error": str(error)},
            )
            return False

        return True

    def health(self) -> bool:
        client = self._get_client()

        if client is None:
            return False

        try:
            return bool(client.ping())
        except Exception:
            return False


redis_cache = RedisCache()
