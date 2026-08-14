import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.monitoring.metrics import metrics


logger = logging.getLogger("library.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        started_at = perf_counter()
        request_id = request.headers.get(
            "X-Request-ID",
            str(uuid4()),
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            self._record_request(
                request,
                status_code=500,
                duration_ms=duration_ms,
            )
            logger.exception(
                "request.unhandled_exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        route_path = self._record_request(
            request,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"

        log_method = logger.info
        if response.status_code >= 500:
            log_method = logger.error
        elif response.status_code >= 400:
            log_method = logger.warning

        log_method(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": route_path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response

    @staticmethod
    def _record_request(
        request: Request,
        status_code: int,
        duration_ms: float,
    ) -> str:
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        metrics.record_request(
            request.method,
            route_path,
            status_code,
            duration_ms,
        )
        return route_path
