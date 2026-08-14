from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from typing import Any


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._started_at = datetime.now(timezone.utc)
            self._started_monotonic = monotonic()
            self._total_requests = 0
            self._error_requests = 0
            self._total_response_ms = 0.0
            self._max_response_ms = 0.0
            self._routes: Counter[str] = Counter()
            self._status_codes: Counter[str] = Counter()
            self._cache: Counter[str] = Counter()

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        route_key = f"{method.upper()} {path}"

        with self._lock:
            self._total_requests += 1
            self._total_response_ms += duration_ms
            self._max_response_ms = max(
                self._max_response_ms,
                duration_ms,
            )
            self._routes[route_key] += 1
            self._status_codes[str(status_code)] += 1

            if status_code >= 400:
                self._error_requests += 1

    def record_cache(self, status: str) -> None:
        with self._lock:
            self._cache[status] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total_requests = self._total_requests
            error_requests = self._error_requests
            cache_hits = self._cache["HIT"]
            cache_misses = self._cache["MISS"]
            cache_attempts = cache_hits + cache_misses

            average_response_ms = (
                self._total_response_ms / total_requests if total_requests else 0.0
            )
            error_rate = (
                error_requests / total_requests * 100 if total_requests else 0.0
            )
            cache_hit_rate = (
                cache_hits / cache_attempts * 100 if cache_attempts else 0.0
            )

            return {
                "started_at": self._started_at.isoformat(),
                "uptime_seconds": round(
                    monotonic() - self._started_monotonic,
                    2,
                ),
                "requests": {
                    "total": total_requests,
                    "errors": error_requests,
                    "error_rate_percent": round(error_rate, 2),
                    "average_response_ms": round(
                        average_response_ms,
                        2,
                    ),
                    "max_response_ms": round(
                        self._max_response_ms,
                        2,
                    ),
                    "by_route": dict(self._routes.most_common()),
                    "by_status_code": dict(self._status_codes),
                },
                "cache": {
                    "hits": cache_hits,
                    "misses": cache_misses,
                    "bypasses": self._cache["BYPASS"],
                    "hit_rate_percent": round(cache_hit_rate, 2),
                },
            }


metrics = MetricsRegistry()
