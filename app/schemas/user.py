# app/schemas/user.py
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    captcha_token: str = Field(..., alias="h-captcha-response")

    model_config = {"populate_by_name": True}

    @field_validator("name")
    @classmethod
    def name_no_html(cls, v: str) -> str:
        if re.search(r"[<>\"'&]", v):
            raise ValueError("Name contains invalid characters")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateName(BaseModel):
    new_name: str = Field(..., min_length=2, max_length=50)

    @field_validator("new_name")
    @classmethod
    def name_no_html(cls, v: str) -> str:
        if re.search(r"[<>\"'&]", v):
            raise ValueError("Name contains invalid characters")
        return v.strip()


class ChangePassword(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class DeleteAccount(BaseModel):
    password: str = Field(..., min_length=1, max_length=100)
    confirmation: str = Field(..., min_length=1)

    @field_validator("confirmation")
    @classmethod
    def must_be_exact(cls, v: str) -> str:
        if v.lower().strip() != "delete my account":
            raise ValueError("Please type 'delete my account' exactly to confirm")
        return v