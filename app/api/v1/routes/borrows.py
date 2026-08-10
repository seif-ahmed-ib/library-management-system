from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, require_member
from app.db.dependencies import get_db
from app.models.borrow_record import BorrowRecord
from app.models.user import User
from app.schemas.borrow_record import BorrowCreate, BorrowRecordRead
from app.services.borrow_service import (
    borrow_book as borrow_book_service,
)
from app.services.borrow_service import (
    get_user_borrow_history,
    list_all_borrow_records,
)
from app.services.borrow_service import (
    return_book as return_book_service,
)


router = APIRouter(
    prefix="/borrows",
    tags=["Borrowing"],
)


def raise_borrow_http_error(error: Exception) -> NoReturn:
    if isinstance(error, LookupError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, PermissionError):
        status_code = status.HTTP_403_FORBIDDEN
    else:
        status_code = status.HTTP_409_CONFLICT

    raise HTTPException(
        status_code=status_code,
        detail=str(error),
    ) from error


@router.post(
    "",
    response_model=BorrowRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def borrow_book(
    borrow_data: BorrowCreate,
    db: Annotated[Session, Depends(get_db)],
    member: Annotated[User, Depends(require_member)],
) -> BorrowRecord:
    try:
        return borrow_book_service(
            db,
            member.id,
            borrow_data.book_id,
        )
    except (LookupError, PermissionError, ValueError) as error:
        raise_borrow_http_error(error)


@router.post(
    "/{borrow_record_id}/return",
    response_model=BorrowRecordRead,
)
def return_book(
    borrow_record_id: int,
    db: Annotated[Session, Depends(get_db)],
    member: Annotated[User, Depends(require_member)],
) -> BorrowRecord:
    try:
        return return_book_service(
            db,
            member.id,
            borrow_record_id,
        )
    except (LookupError, PermissionError, ValueError) as error:
        raise_borrow_http_error(error)


@router.get(
    "/me/history",
    response_model=list[BorrowRecordRead],
)
def read_personal_history(
    db: Annotated[Session, Depends(get_db)],
    member: Annotated[User, Depends(require_member)],
    skip: int = 0,
    limit: int = 100,
) -> list[BorrowRecord]:
    return get_user_borrow_history(
        db,
        member.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "",
    response_model=list[BorrowRecordRead],
)
def read_all_borrow_records(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
    skip: int = 0,
    limit: int = 100,
) -> list[BorrowRecord]:
    return list_all_borrow_records(
        db,
        skip=skip,
        limit=limit,
    )
