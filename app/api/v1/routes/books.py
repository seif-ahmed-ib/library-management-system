from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_active_user,
    require_admin,
)
from app.db.dependencies import get_db
from app.models.book import Book
from app.models.user import User
from app.schemas.book import (
    BookCreate,
    BookRead,
    BookUpdate,
)
from app.services.book_service import (
    create_book as create_book_service,
)
from app.services.book_service import (
    delete_book as delete_book_service,
)
from app.services.book_service import (
    get_book as get_book_service,
)
from app.services.book_service import (
    list_books as list_books_service,
)
from app.services.book_service import (
    update_book as update_book_service,
)


router = APIRouter(
    prefix="/books",
    tags=["Books"],
)


@router.get(
    "",
    response_model=list[BookRead],
)
def read_books(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> list[Book]:
    return list_books_service(db)


@router.get(
    "/{book_id}",
    response_model=BookRead,
)
def read_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> Book:
    try:
        return get_book_service(db, book_id)

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
)
def create_book(
    book_data: BookCreate,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[
        User,
        Depends(require_admin),
    ],
) -> Book:
    try:
        return create_book_service(db, book_data)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.put(
    "/{book_id}",
    response_model=BookRead,
)
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[
        User,
        Depends(require_admin),
    ],
) -> Book:
    try:
        return update_book_service(
            db,
            book_id,
            book_data,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[
        User,
        Depends(require_admin),
    ],
) -> Response:
    try:
        delete_book_service(db, book_id)

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )