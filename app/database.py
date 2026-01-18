"""
Database connection and session management
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine
# For PostgreSQL on Supabase, we need to configure the connection
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=300,    # Recycle connections after 5 minutes
    echo=False           # Set to True to see SQL queries (for debugging)
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    """
    Dependency function that yields a database session.
    FastAPI will automatically close the session after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")


# Test connection
def test_connection():
    """Test database connection"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Function to close database connection
def disconnect():
    """Close database connection pool"""
    if engine:
        engine.dispose()
        print("✅ Database connections closed")
