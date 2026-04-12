# app/schemas/__init__.py
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    UpdateName,
    ChangePassword,
    DeleteAccount,
)
from app.schemas.book import (
    BookResponse,
    BookSuggestionCreate,
    BookSuggestionResponse,
    BookUpdate,
    SetCurrentBook,
)
from app.schemas.progress import (
    ProgressUpdate,
    ProgressResponse,
    CommunityProgressResponse,
)
from app.schemas.meeting import (
    MeetingUpdate,
    MeetingResponse,
)
from app.schemas.access_code import (
    AccessCodeVerify,
    AccessCodeUpdate,
    AccessCodeResponse,
)
from app.schemas.admin import (
    AdminStatsResponse,
    AdminLogResponse,
    AdminLogDetailResponse,
)
from app.schemas.feedback import FeedbackCreate

__all__ = [
    # User
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "UpdateName",
    "ChangePassword",
    "DeleteAccount",
    # Book
    "BookResponse",
    "BookSuggestionCreate",
    "BookSuggestionResponse",
    "BookUpdate",
    "SetCurrentBook",
    # Progress
    "ProgressUpdate",
    "ProgressResponse",
    "CommunityProgressResponse",
    # Meeting
    "MeetingUpdate",
    "MeetingResponse",
    # Access code
    "AccessCodeVerify",
    "AccessCodeUpdate",
    "AccessCodeResponse",
    # Admin
    "AdminStatsResponse",
    "AdminLogResponse",
    "AdminLogDetailResponse",
    # Feedback
    "FeedbackCreate",
]