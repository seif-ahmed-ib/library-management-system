"""Add realistic, repeatable demo data without deleting existing records."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.book import Book
from app.models.borrow_record import BorrowRecord
from app.models.user import User, UserRole


DEMO_PASSWORD = "Member123!"

DEMO_USERS = [
    ("Mariam Hassan", "mariam@library.demo"),
    ("Omar Khaled", "omar@library.demo"),
    ("Nour Ahmed", "nour@library.demo"),
]

DEMO_BOOKS = [
    ("Clean Code", "Robert C. Martin", "9780132350884", 4),
    ("The Pragmatic Programmer", "Andrew Hunt", "9780135957059", 3),
    ("Designing Data-Intensive Applications", "Martin Kleppmann", "9781449373320", 3),
    ("Python Crash Course", "Eric Matthes", "9781718502703", 5),
    ("Automate the Boring Stuff with Python", "Al Sweigart", "9781593279929", 4),
    ("Fluent Python", "Luciano Ramalho", "9781492056355", 2),
    ("Introduction to Algorithms", "Thomas H. Cormen", "9780262046305", 3),
    ("Database System Concepts", "Abraham Silberschatz", "9780078022159", 4),
    ("Fundamentals of Data Engineering", "Joe Reis", "9781098108304", 3),
    ("Storytelling with Data", "Cole Nussbaumer Knaflic", "9781119002253", 3),
    ("The Data Warehouse Toolkit", "Ralph Kimball", "9781118530801", 2),
    ("Dune", "Frank Herbert", "9780441172719", 2),
    ("The Hobbit", "J. R. R. Tolkien", "9780547928227", 4),
    ("Atomic Habits", "James Clear", "9780735211292", 5),
    ("Deep Work", "Cal Newport", "9781455586691", 3),
]


def get_or_create_users(db: Session) -> list[User]:
    users: list[User] = []
    hashed_password = get_password_hash(DEMO_PASSWORD)

    for full_name, email in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                full_name=full_name,
                email=email,
                hashed_password=hashed_password,
                role=UserRole.MEMBER,
                is_active=True,
            )
            db.add(user)
            db.flush()
        users.append(user)

    return users


def get_or_create_books(db: Session) -> list[Book]:
    books: list[Book] = []

    for title, author, isbn, copies in DEMO_BOOKS:
        book = db.scalar(select(Book).where(Book.isbn == isbn))
        if book is None:
            book = Book(
                title=title,
                author=author,
                isbn=isbn,
                total_copies=copies,
                available_copies=copies,
            )
            db.add(book)
            db.flush()
        books.append(book)

    return books


def add_borrow_history(
    db: Session,
    users: list[User],
    books: list[Book],
) -> int:
    demo_user_ids = [user.id for user in users]
    existing_record = db.scalar(
        select(BorrowRecord.id).where(BorrowRecord.user_id.in_(demo_user_ids))
    )
    if existing_record is not None:
        return 0

    now = datetime.now(timezone.utc)
    record_specs = [
        (0, 0, 18, 11),
        (0, 3, 10, 5),
        (0, 11, 2, None),
        (1, 2, 25, 17),
        (1, 7, 8, 3),
        (1, 11, 1, None),
        (2, 4, 15, 9),
        (2, 9, 6, None),
        (2, 13, 3, None),
    ]

    for user_index, book_index, borrowed_days_ago, returned_days_ago in record_specs:
        book = books[book_index]
        returned_at = (
            now - timedelta(days=returned_days_ago)
            if returned_days_ago is not None
            else None
        )
        db.add(
            BorrowRecord(
                user_id=users[user_index].id,
                book_id=book.id,
                borrowed_at=now - timedelta(days=borrowed_days_ago),
                returned_at=returned_at,
            )
        )
        if returned_at is None:
            book.available_copies -= 1

    return len(record_specs)


def seed_demo_data() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        users = get_or_create_users(db)
        books = get_or_create_books(db)
        record_count = add_borrow_history(db, users, books)
        db.commit()

    print("Demo data is ready.")
    print(f"Books available in seed set: {len(books)}")
    print(f"Demo members available: {len(users)}")
    print(f"Borrow records added this run: {record_count}")
    print(f"Demo member password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed_demo_data()
