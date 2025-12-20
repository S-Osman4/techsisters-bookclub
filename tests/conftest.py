"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, AccessCode, Book, Meeting, BookSuggestion, ReadingProgress

# Use in-memory SQLite for testing (faster than PostgreSQL)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Create a test client with overridden database"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def access_code(db):
    """Create test access code"""
    code = AccessCode(code="TEST2024")
    db.add(code)
    db.commit()
    db.refresh(code)
    return code

@pytest.fixture(scope="function")
def test_user(db):
    """Create regular test user"""
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash=User.hash_password("password123"),
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(scope="function")
def admin_user(db):
    """Create admin test user"""
    admin = User(
        name="Admin User",
        email="admin@example.com",
        password_hash=User.hash_password("admin123"),
        is_admin=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin

@pytest.fixture(scope="function")
def current_book(db):
    """Create current book"""
    book = Book(
        title="Test Book",
        pdf_url="https://example.com/test.pdf",
        status="current",
        current_chapters="Chapters 1-2",
        total_chapters=10
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book

@pytest.fixture(scope="function")
def queued_book(db):
    """Create queued book"""
    book = Book(
        title="Queued Book",
        pdf_url="https://example.com/queued.pdf",
        status="queued",
        total_chapters=8
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book

@pytest.fixture(scope="function")
def meeting(db):
    """Create test meeting"""
    meeting = Meeting(
        date="December 20, 2024",
        time="7:00 PM EAT",
        meet_link="https://meet.google.com/test"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting

@pytest.fixture(scope="function")
def authenticated_client(client, test_user):
    """Create client with authenticated session"""
    # Manually set session (simulating login)
    with client:
        with client.session_transaction() as session:
            session["user_id"] = test_user.id
            session["user_name"] = test_user.name
            session["is_admin"] = test_user.is_admin
    return client

@pytest.fixture(scope="function")
def admin_client(client, admin_user):
    """Create client with admin session"""
    with client:
        with client.session_transaction() as session:
            session["user_id"] = admin_user.id
            session["user_name"] = admin_user.name
            session["is_admin"] = admin_user.is_admin
    return client