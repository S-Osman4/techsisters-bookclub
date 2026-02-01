"""
SQLAlchemy Database Models

"""
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import bcrypt  # ✅ SECURE: Direct bcrypt import (no passlib dependency)
from app.database import Base

class AccessCode(Base):
    """Single active access code for guest access"""
    __tablename__ = "access_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AccessCode(code='{self.code}')>"


class User(Base):
    """Registered members of the book club"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    book_suggestions = relationship(
        "BookSuggestion", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    reading_progress = relationship(
        "ReadingProgress", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    
    def verify_password(self, password: str) -> bool:
        """
        Verify password against stored bcrypt hash
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        try:
            # bcrypt.checkpw expects bytes, not strings
            return bcrypt.checkpw(
                password.encode('utf-8'),  # Convert input to bytes
                self.password_hash.encode('utf-8')  # Convert stored hash to bytes
            )
        except (ValueError, AttributeError, UnicodeDecodeError):
            # Handle cases where:
            # 1. Hash is malformed or not a valid bcrypt hash
            # 2. Password is None or empty
            # 3. Encoding fails
            return False
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with automatic salt generation
        
        Args:
            password: Plain text password to hash
            
        Returns:
            str: Bcrypt hash as string (for database storage)
        """
        # bcrypt.hashpw expects bytes
        password_bytes = password.encode('utf-8')
        
        # Generate hash with salt (bcrypt.gensalt() creates optimal salt)
        hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        
        # Return as string for database storage
        return hashed_bytes.decode('utf-8')
    
    def __repr__(self):
        return f"<User(name='{self.name}', email='{self.email}')>"


class Book(Base):
    """Books - can be current, queued, or completed"""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    pdf_url = Column(String(500), nullable=False)
    cover_image_url = Column(String(500), nullable=True)
    total_chapters = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, index=True)  # 'current', 'queued', 'completed'
    current_chapters = Column(String(100), nullable=True)  # e.g., "Chapters 3-4" (only for current)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    reading_progress = relationship(
        "ReadingProgress", 
        back_populates="book", 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Book(title='{self.title}', status='{self.status}')>"


class BookSuggestion(Base):
    """Book suggestions from members"""
    __tablename__ = "book_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    pdf_url = Column(String(500), nullable=False)
    cover_image_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="book_suggestions")
    
    def __repr__(self):
        return f"<BookSuggestion(title='{self.title}', status='{self.status}')>"


class Meeting(Base):
    """Current meeting details (single row)"""
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, index=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    meet_link = Column(String(500), nullable=False)  # Google Meet URL
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Meeting(start_at='{self.start_at.isoformat()}', meet_link='{self.meet_link}')>"


class ReadingProgress(Base):
    """Individual member reading progress"""
    __tablename__ = "reading_progress"
    __table_args__ = (UniqueConstraint('user_id', 'book_id', name='_user_book_uc'),)
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter = Column(Integer, nullable=False)  # 0 = not started, -1 = completed, 1+ = current chapter
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reading_progress")
    book = relationship("Book", back_populates="reading_progress")
    
    def __repr__(self):
        return f"<ReadingProgress(user_id={self.user_id}, book_id={self.book_id}, chapter={self.chapter})>"


class AdminAction(Base):
    """Audit log for admin actions"""
    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    target = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    admin = relationship("User")

    def __repr__(self):
        return f"<AdminAction(admin_id={self.admin_id}, action='{self.action}')>"
    
class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    email = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="feedback_items")