# app/schemas/access_code.py
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re


class AccessCodeVerify(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)

    @field_validator("code")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().upper()


class AccessCodeUpdate(BaseModel):
    new_code: str = Field(..., min_length=4, max_length=50)

    @field_validator("new_code")
    @classmethod
    def normalise_and_validate(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError("Access code must contain only letters and numbers")
        return v


class AccessCodeResponse(BaseModel):
    code: str
    updated_at: datetime

    model_config = {"from_attributes": True}