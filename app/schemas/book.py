# app/schemas/book.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


def _require_https(v: Optional[str]) -> Optional[str]:
    """Shared URL validator — ensures http/https scheme."""
    if v and not v.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return v


class BookResponse(BaseModel):
    id: int
    title: str
    pdf_url: str
    cover_image_url: Optional[str]
    total_chapters: Optional[int]
    status: str
    current_chapters: Optional[str]   # stored string, e.g. "Chapters 1–3"
    completed_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookSuggestionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    pdf_url: str = Field(..., max_length=500)
    cover_image_url: Optional[str] = Field(None, max_length=500)

    @field_validator("pdf_url")
    @classmethod
    def validate_pdf_url(cls, v: str) -> str:
        return _require_https(v)  # type: ignore[return-value]

    @field_validator("cover_image_url")
    @classmethod
    def validate_cover_url(cls, v: Optional[str]) -> Optional[str]:
        return _require_https(v)


class BookSuggestionResponse(BaseModel):
    id: int
    title: str
    pdf_url: str
    cover_image_url: Optional[str]
    status: str
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BookUpdate(BaseModel):
    """
    All fields optional — only provided fields are updated.
    Admin sends chapter_from / chapter_to; the service converts them
    to a current_chapters string before writing to the DB.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    pdf_url: Optional[str] = Field(None, max_length=500)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    chapter_from: Optional[int] = Field(None, ge=1)
    chapter_to: Optional[int] = Field(None, ge=1)
    total_chapters: Optional[int] = Field(None, ge=1)

    @field_validator("pdf_url")
    @classmethod
    def validate_pdf_url(cls, v: Optional[str]) -> Optional[str]:
        return _require_https(v)

    @field_validator("cover_image_url")
    @classmethod
    def validate_cover_url(cls, v: Optional[str]) -> Optional[str]:
        return _require_https(v)

    @model_validator(mode="after")
    def chapter_to_gte_from(self) -> "BookUpdate":
        if (
            self.chapter_from is not None
            and self.chapter_to is not None
            and self.chapter_to < self.chapter_from
        ):
            raise ValueError("chapter_to must be >= chapter_from")
        return self


class SetCurrentBook(BaseModel):
    """
    Payload when moving a queued book to current.
    chapter_from is required. chapter_to defaults to chapter_from
    (single chapter) if omitted.
    """
    chapter_from: int = Field(..., ge=1)
    chapter_to: Optional[int] = Field(None, ge=1)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    total_chapters: Optional[int] = Field(None, ge=1)

    @field_validator("cover_image_url")
    @classmethod
    def validate_cover_url(cls, v: Optional[str]) -> Optional[str]:
        return _require_https(v)

    @model_validator(mode="after")
    def chapter_to_gte_from(self) -> "SetCurrentBook":
        if self.chapter_to is not None and self.chapter_to < self.chapter_from:
            raise ValueError("chapter_to must be >= chapter_from")
        return self