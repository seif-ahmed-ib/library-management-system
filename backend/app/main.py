import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.books import router as books_router
from app.api.v1.routes.borrows import router as borrows_router
from app.api.v1.routes.monitoring import router as monitoring_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.base import Base
from app.db.session import engine
from app.frontend.router import FRONTEND_DIR, router as frontend_router
from app.middleware.request_logging import RequestLoggingMiddleware


configure_logging()
logger = logging.getLogger("library.lifecycle")


@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError:
        logger.critical(
            "application.database_initialization_failed",
            exc_info=True,
        )
        raise

    logger.info("application.started")
    yield
    engine.dispose()
    logger.info("application.stopped")


app = FastAPI(
    title=settings.app_name,
    description=("Backend API for managing books and borrowing operations."),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(
    auth_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    books_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    borrows_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(monitoring_router)
app.include_router(frontend_router)
app.mount(
    "/app/assets",
    StaticFiles(directory=FRONTEND_DIR / "assets"),
    name="frontend-assets",
)


@app.get("/", tags=["Health"])
def read_root() -> dict[str, str]:
    return {"message": ("Library Management System API is running")}
