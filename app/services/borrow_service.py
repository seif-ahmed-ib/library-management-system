import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cache.book_cache import book_cache
from app.core.config import settings
from app.models.book import Book
from app.models.borrow_record import BorrowRecord
from app.models.user import User


logger = logging.getLogger("library.borrows")


def borrow_book(
    db: Session,
    user_id: int,
    book_id: int,
) -> BorrowRecord:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())

    if user is None:
        raise LookupError("User not found.")

    if not user.is_active:
        raise PermissionError("Inactive users cannot borrow books.")

    book = db.scalar(select(Book).where(Book.id == book_id).with_for_update())

    if book is None:
        raise LookupError("Book not found.")

    if book.available_copies <= 0:
        raise ValueError("No available copies of this book.")

    existing_borrow = db.scalar(
        select(BorrowRecord).where(
            BorrowRecord.user_id == user_id,
            BorrowRecord.book_id == book_id,
            BorrowRecord.returned_at.is_(None),
        )
    )

    if existing_borrow is not None:
        raise ValueError("You have already borrowed this book.")

    active_borrow_count = db.scalar(
        select(func.count(BorrowRecord.id)).where(
            BorrowRecord.user_id == user_id,
            BorrowRecord.returned_at.is_(None),
        )
    )

    if (
        active_borrow_count is not None
        and active_borrow_count >= settings.max_borrowed_books
    ):
        raise ValueError(
            f"You cannot borrow more than {settings.max_borrowed_books} books."
        )

    borrow_record = BorrowRecord(
        user_id=user_id,
        book_id=book_id,
    )

    book.available_copies -= 1

    db.add(borrow_record)
    db.commit()
    db.refresh(borrow_record)

    book_cache.invalidate(book.id)
    logger.info(
        "borrow.created",
        extra={
            "borrow_record_id": borrow_record.id,
            "user_id": user_id,
            "book_id": book_id,
        },
    )

    return borrow_record


def return_book(
    db: Session,
    user_id: int,
    borrow_record_id: int,
) -> BorrowRecord:
    borrow_record = db.scalar(
        select(BorrowRecord)
        .where(BorrowRecord.id == borrow_record_id)
        .with_for_update()
    )

    if borrow_record is None:
        raise LookupError("Borrow record not found.")

    if borrow_record.user_id != user_id:
        raise PermissionError("You cannot return another user's book.")

    if borrow_record.returned_at is not None:
        raise ValueError("This book has already been returned.")

    book = db.scalar(
        select(Book).where(Book.id == borrow_record.book_id).with_for_update()
    )

    if book is None:
        raise LookupError("Book not found.")

    borrow_record.returned_at = datetime.now(timezone.utc)
    book.available_copies += 1

    db.commit()
    db.refresh(borrow_record)

    book_cache.invalidate(book.id)
    logger.info(
        "borrow.returned",
        extra={
            "borrow_record_id": borrow_record.id,
            "user_id": user_id,
            "book_id": book.id,
        },
    )

    return borrow_record


def get_user_borrow_history(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[BorrowRecord]:
    statement = (
        select(BorrowRecord)
        .where(BorrowRecord.user_id == user_id)
        .order_by(BorrowRecord.borrowed_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def list_all_borrow_records(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[BorrowRecord]:
    statement = (
        select(BorrowRecord)
        .order_by(BorrowRecord.borrowed_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())
