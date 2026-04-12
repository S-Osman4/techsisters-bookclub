# app/schemas/meeting.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MeetingUpdate(BaseModel):
    start_at_local: str = Field(
        ...,
        description="Local datetime in ISO format: 2025-01-10T18:30",
    )
    timezone: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="IANA timezone name e.g. Europe/London",
    )
    meet_link: str = Field(..., max_length=500)
    is_cancelled: bool = False
    cancellation_note: Optional[str] = Field(None, max_length=200)

    @field_validator("meet_link")
    @classmethod
    def validate_meet_link(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Meeting link must start with http:// or https://")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            raise ValueError(f"Invalid timezone: {v!r}")
        return v


class MeetingResponse(BaseModel):
    id: int
    start_at: datetime
    meet_link: str
    is_cancelled: bool
    cancellation_note: Optional[str]
    updated_at: datetime

    model_config = {"from_attributes": True}