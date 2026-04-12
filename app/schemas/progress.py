# app/schemas/progress.py
from datetime import datetime
from pydantic import BaseModel, Field


class ProgressUpdate(BaseModel):
    book_id: int = Field(..., gt=0)
    chapter: int = Field(..., ge=-1)
    # ge=-1 allows: -1 (completed), 0 (not started), 1+ (chapter number)


class ProgressResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    chapter: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChapterRangeStat(BaseModel):
    """A single bucket in the community progress breakdown."""
    label: str        # e.g. "Chapters 1-2", "Completed", "Not Started"
    count: int
    percentage: float


class CommunityProgressResponse(BaseModel):
    book_id: int
    book_title: str
    total_readers: int
    stats: list[ChapterRangeStat]