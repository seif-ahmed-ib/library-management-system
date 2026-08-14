from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["Frontend"])
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_PATH = FRONTEND_DIR / "index.html"


@router.get(
    "/app",
    response_class=FileResponse,
    include_in_schema=False,
)
def library_frontend() -> FileResponse:
    return FileResponse(FRONTEND_PATH)
