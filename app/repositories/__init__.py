# app/repositories/__init__.py
from app.repositories.user import UserRepository
from app.repositories.book import BookRepository
from app.repositories.book_suggestion import BookSuggestionRepository
from app.repositories.reading_progress import ReadingProgressRepository
from app.repositories.meeting import MeetingRepository
from app.repositories.access_code import AccessCodeRepository
from app.repositories.admin_action import AdminActionRepository
from app.repositories.feedback import FeedbackRepository

__all__ = [
    "UserRepository",
    "BookRepository",
    "BookSuggestionRepository",
    "ReadingProgressRepository",
    "MeetingRepository",
    "AccessCodeRepository",
    "AdminActionRepository",
    "FeedbackRepository",
]