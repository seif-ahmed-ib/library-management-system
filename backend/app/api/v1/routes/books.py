from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_active_user,
    require_admin,
)
from app.cache.book_cache import book_cache
from app.cache.redis_cache import CacheStatus
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
    list_available_books as list_available_books_service,
)
from app.services.book_service import (
    list_books as list_books_service,
)
from app.services.book_service import (
    search_books as search_books_service,
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
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Book] | list[dict[str, Any]]:
    lookup = book_cache.get_list(skip, limit)
    response.headers["X-Cache"] = lookup.status.value

    if lookup.status == CacheStatus.HIT:
        return lookup.value

    books = list_books_service(
        db,
        skip=skip,
        limit=limit,
    )

    book_cache.set_list(
        skip,
        limit,
        [
            BookRead.model_validate(book).model_dump(mode="json")
            for book in books
        ],
    )
    return books


@router.get(
    "/available",
    response_model=list[BookRead],
)
def read_available_books(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Book]:
    return list_available_books_service(
        db,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=list[BookRead],
)
def search_books(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
    query: str = Query(min_length=1, max_length=200),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Book]:
    return search_books_service(
        db,
        query=query,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{book_id}",
    response_model=BookRead,
)
def read_book(
    book_id: int,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> Book | dict[str, Any]:
    lookup = book_cache.get_item(book_id)
    response.headers["X-Cache"] = lookup.status.value

    if lookup.status == CacheStatus.HIT:
        return lookup.value

    try:
        book = get_book_service(db, book_id)

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    book_cache.set_item(
        book_id,
        BookRead.model_validate(book).model_dump(mode="json"),
    )
    return book


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

    return Response(status_code=status.HTTP_204_NO_CONTENT)
