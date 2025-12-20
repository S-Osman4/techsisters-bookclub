#!/usr/bin/env python3
"""
Migration: Add cover_image_url to books table
"""
from app.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """Add cover_image_url column to books table"""
    print("🔄 Running migration: Add book cover images...")
    
    db = SessionLocal()
    
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='books' AND column_name='cover_image_url'
        """))
        
        if result.fetchone():
            print("⚠️  Column 'cover_image_url' already exists. Skipping migration.")
            return
        
        # Add the column
        db.execute(text("""
            ALTER TABLE books 
            ADD COLUMN cover_image_url VARCHAR(500) NULL
        """))
        
        db.commit()
        print("✅ Migration successful: cover_image_url column added to books table")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()