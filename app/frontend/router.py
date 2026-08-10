from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["Frontend"])
FRONTEND_PATH = Path(__file__).with_name("index.html")


@router.get(
    "/app",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def library_frontend() -> HTMLResponse:
    return HTMLResponse(FRONTEND_PATH.read_text(encoding="utf-8"))
