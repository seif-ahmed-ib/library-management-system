from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


BookTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]

BookAuthor = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]

BookISBN = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=10,
        max_length=20,
    ),
]


class BookBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: BookTitle
    author: BookAuthor
    isbn: BookISBN


class BookCreate(BookBase):
    total_copies: int = Field(default=1, ge=1)


class BookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: BookTitle | None = None
    author: BookAuthor | None = None
    isbn: BookISBN | None = None
    total_copies: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_update_data(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")

        return self


class BookRead(BookBase):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: int
    total_copies: int
    available_copies: int
    created_at: datetime
    updated_at: datetime
