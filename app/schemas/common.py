# app/schemas/common.py
from typing import Any, Optional
from pydantic import BaseModel


class MessageResponse(BaseModel):
    """
    Generic success response used across all endpoints.
    Routes return this when there is no specific data to return.
    """
    message: str
    success: bool = True


class SuccessResponse(BaseModel):
    """
    Success response that optionally carries a data payload.
    Used when the caller needs the created/updated object back.
    """
    success: bool = True
    message: str = ""
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """
    Standard error shape returned on all 4xx/5xx responses.
    """
    detail: str
    success: bool = False