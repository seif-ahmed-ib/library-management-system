from fastapi import FastAPI

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.books import router as books_router
from app.api.v1.routes.borrows import router as borrows_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description=("Backend API for managing books and borrowing operations."),
    version="1.0.0",
)

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


@app.get("/", tags=["Health"])
def read_root() -> dict[str, str]:
    return {"message": ("Library Management System API is running")}
