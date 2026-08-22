import logging

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.cache.book_cache import book_cache
from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate


logger = logging.getLogger("library.books")


def create_book(db: Session, book_data: BookCreate) -> Book:
    existing_book = db.scalar(select(Book).where(Book.isbn == book_data.isbn))

    if existing_book:
        raise ValueError("A book with this ISBN already exists.")

    book = Book(
        title=book_data.title,
        author=book_data.author,
        isbn=book_data.isbn,
        total_copies=book_data.total_copies,
        available_copies=book_data.total_copies,
    )

    db.add(book)
    db.commit()
    db.refresh(book)

    book_cache.invalidate()
    logger.info(
        "book.created",
        extra={"book_id": book.id, "isbn": book.isbn},
    )

    return book


def get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)

    if book is None:
        raise LookupError("Book not found.")

    return book


def get_book_by_isbn(db: Session, isbn: str) -> Book | None:
    return db.scalar(select(Book).where(Book.isbn == isbn))


def list_books(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[Book]:
    statement = select(Book).order_by(Book.id).offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def search_books(
    db: Session,
    query: str,
    skip: int = 0,
    limit: int = 100,
) -> list[Book]:
    search_pattern = f"%{query.strip()}%"

    statement = (
        select(Book)
        .where(
            or_(
                Book.title.ilike(search_pattern),
                Book.author.ilike(search_pattern),
                Book.isbn.ilike(search_pattern),
            )
        )
        .order_by(Book.id)
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def update_book(
    db: Session,
    book_id: int,
    book_data: BookUpdate,
) -> Book:
    book = get_book(db, book_id)
    update_data = book_data.model_dump(exclude_unset=True)

    if "isbn" in update_data:
        existing_book = get_book_by_isbn(db, update_data["isbn"])

        if existing_book and existing_book.id != book.id:
            raise ValueError("A book with this ISBN already exists.")

    if "total_copies" in update_data:
        borrowed_copies = book.total_copies - book.available_copies
        new_total_copies = update_data["total_copies"]

        if new_total_copies < borrowed_copies:
            raise ValueError("Total copies cannot be less than borrowed copies.")

        book.available_copies = new_total_copies - borrowed_copies

    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)

    book_cache.invalidate(book.id)
    logger.info(
        "book.updated",
        extra={"book_id": book.id, "fields": sorted(update_data)},
    )

    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book(db, book_id)

    if book.available_copies != book.total_copies:
        raise ValueError("A borrowed book cannot be deleted.")

    isbn = book.isbn
    db.delete(book)
    db.commit()

    book_cache.invalidate(book_id)
    logger.info(
        "book.deleted",
        extra={"book_id": book_id, "isbn": isbn},
    )
