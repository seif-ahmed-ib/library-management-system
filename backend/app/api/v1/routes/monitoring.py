import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.cache.redis_cache import redis_cache
from app.core.logging_config import get_recent_logs
from app.db.dependencies import get_db
from app.monitoring.metrics import metrics


router = APIRouter(tags=["Monitoring"])
logger = logging.getLogger("library.monitoring")
DASHBOARD_PATH = Path(__file__).resolve().parents[3] / "monitoring" / "dashboard.html"


def get_system_health(db: Session) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        database_status = "healthy"
    except SQLAlchemyError as error:
        database_status = "unavailable"
        logger.error(
            "health.database_unavailable",
            extra={"error": str(error)},
        )

    redis_status = "healthy" if redis_cache.health() else "unavailable"
    overall_status = (
        "healthy" if database_status == redis_status == "healthy" else "degraded"
    )

    return {
        "status": overall_status,
        "application": "healthy",
        "database": database_status,
        "redis": redis_status,
    }


@router.get("/health")
def health_check(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    return get_system_health(db)


@router.get("/monitoring/data")
def monitoring_data(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    snapshot = metrics.snapshot()
    snapshot["health"] = get_system_health(db)
    snapshot["recent_errors"] = get_recent_logs(
        minimum_level=logging.WARNING,
        limit=20,
    )
    return snapshot


@router.get(
    "/monitoring",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def monitoring_dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))
