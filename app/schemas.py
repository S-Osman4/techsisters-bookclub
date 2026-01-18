"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from datetime import datetime
from typing import Optional, Literal

# ===== User Schemas =====
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ===== Book Schemas =====
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    pdf_url: str
    cover_image_url: Optional[str] = None

class BookCreate(BookBase):
    total_chapters: Optional[int] = None
    status: Literal["current", "queued", "completed"] = "queued"

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    pdf_url: Optional[str] = None
    cover_image_url: Optional[str] = None 
    current_chapters: Optional[str] = Field(None, max_length=100)
    total_chapters: Optional[int] = None

class BookResponse(BookBase):
    id: int
    status: str
    current_chapters: Optional[str] = None
    total_chapters: Optional[int] = None
    cover_image_url: Optional[str] = None
    completed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ===== Book Suggestion Schemas =====
class SuggestionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    pdf_url: str
    cover_image_url: Optional[str] = None

class SuggestionUpdate(BaseModel):
    status: Literal["approved", "rejected"]

class SuggestionResponse(BaseModel):
    id: int
    title: str
    pdf_url: str
    cover_image_url: Optional[str] = None
    status: str
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ===== Meeting Schemas =====
class MeetingUpdate(BaseModel):
    start_at_local: datetime = Field(..., description="Local meeting datetime")
    timezone: str = Field(..., min_length=1, max_length=50)  # e.g. "Africa/Nairobi"
    meet_link: HttpUrl

class MeetingResponse(BaseModel):
    id: int
    start_at: datetime
    meet_link: str
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ===== Reading Progress Schemas =====
class ProgressUpdate(BaseModel):
    book_id: int
    chapter: int = Field(..., ge=-1)

class ProgressResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    chapter: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ===== Access Code Schemas =====
class CodeVerify(BaseModel):
    code: str = Field(..., min_length=1)

class CodeUpdate(BaseModel):
    new_code: str = Field(..., min_length=5, max_length=50)

class CodeResponse(BaseModel):
    code: str
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ===== Response Messages =====
class MessageResponse(BaseModel):
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    detail: str
    success: bool = False