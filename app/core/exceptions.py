# app/core/exceptions.py
from typing import Any


class AppError(Exception):
    """
    Base exception for all application domain errors.
    Routes catch AppError subclasses and map them to HTTP responses.
    """

    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str | None = None, **kwargs: Any) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action"


class ConflictError(AppError):
    status_code = 409
    detail = "Resource already exists"


class ValidationError(AppError):
    status_code = 422
    detail = "Invalid input"


class RateLimitError(AppError):
    status_code = 429
    detail = "Too many requests. Please try again later"


class ExternalServiceError(AppError):
    status_code = 502
    detail = "An external service is unavailable"