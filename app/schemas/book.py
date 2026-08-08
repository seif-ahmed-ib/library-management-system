from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    isbn: str = Field(min_length=10, max_length=20)


class BookCreate(BookBase):
    total_copies: int = Field(default=1, ge=1)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=100)
    isbn: str | None = Field(default=None, min_length=10, max_length=20)
    total_copies: int | None = Field(default=None, ge=1)


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_copies: int
    available_copies: int
    created_at: datetime
    updated_at: datetime