from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BorrowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    book_id: int = Field(gt=0)


class BorrowRecordRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    returned_at: datetime | None
