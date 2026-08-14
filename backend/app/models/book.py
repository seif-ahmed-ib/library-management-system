from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.borrow_record import BorrowRecord


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint(
            "total_copies >= 1",
            name="check_total_copies_positive",
        ),
        CheckConstraint(
            "available_copies >= 0 AND available_copies <= total_copies",
            name="check_available_copies_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    author: Mapped[str] = mapped_column(String(100), index=True)
    isbn: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )
    total_copies: Mapped[int] = mapped_column(default=1)
    available_copies: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    borrow_records: Mapped[list[BorrowRecord]] = relationship(
        back_populates="book",
    )
