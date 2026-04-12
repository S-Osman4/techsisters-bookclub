# app/schemas/feedback.py
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator

class FeedbackCreate(BaseModel):
    type: Literal["bug", "suggestion", "feedback"]
    message: str = Field(..., min_length=1, max_length=2000)
    email: Optional[EmailStr] = None

    @field_validator("email", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v