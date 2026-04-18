# app/schemas/common.py
from pydantic import BaseModel
from typing import Any, Optional


class MessageResponse(BaseModel):
    """
    Generic success response used across all endpoints.
    Routes return this when there is no specific data to return.
    """
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """
    Standard error shape returned on all 4xx/5xx responses.
    """
    detail: str
    success: bool = False

class SuccessResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None