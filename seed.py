"""
Seed database with initial data
"""
from app.database import SessionLocal, create_tables
from app.models import User, AccessCode, Book, Meeting
from datetime import datetime

def seed_database():
    """Seed the database with initial data"""
    print("🌱 Starting database seed...")
    
    # Create tables if they don't exist
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # 1. Create Access Code
        print("📝 Creating access code...")
        existing_code = db.query(AccessCode).first()
        if not existing_code:
            access_code = AccessCode(code="TW2024DEC")
            db.add(access_code)
            print("   ✅ Access code: TW2024DEC")
        else:
            print(f"   ⚠️  Access code already exists: {existing_code.code}")
        
        # 2. Create Admin User
        print("👤 Creating admin user...")
        existing_admin = db.query(User).filter(User.email == "admin@bookclub.com").first()
        if not existing_admin:
            admin = User(
                name="Admin",
                email="admin@bookclub.com",
                password_hash=User.hash_password("admin123"),
                is_admin=True
            )
            db.add(admin)
            print("   ✅ Admin user created")
            print("      Email: admin@bookclub.com")
            print("      Password: admin123")
            print("      ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")
        else:
            print("   ⚠️  Admin user already exists")
        
        # 3. Create Test User
        print("👤 Creating test user...")
        existing_test = db.query(User).filter(User.email == "test@example.com").first()
        if not existing_test:
            test_user = User(
                name="Test User",
                email="test@example.com",
                password_hash=User.hash_password("password123"),
                is_admin=False
            )
            db.add(test_user)
            print("   ✅ Test user created")
            print("      Email: test@example.com")
            print("      Password: password123")
        else:
            print("   ⚠️  Test user already exists")
        
        # 4. Create Current Book
        print("📚 Creating current book...")
        existing_current = db.query(Book).filter(Book.status == "current").first()
        if not existing_current:
            current_book = Book(
                title="The Pragmatic Programmer",
                pdf_url="https://example.com/pragmatic-programmer.pdf",
                status="current",
                current_chapters="Chapters 1-2",
                total_chapters=10
            )
            db.add(current_book)
            print("   ✅ Current book: The Pragmatic Programmer")
        else:
            print(f"   ⚠️  Current book already exists: {existing_current.title}")
        
        # 5. Create Queued Books
        print("📚 Creating queued books...")
        queued_books = [
            {
                "title": "Clean Code",
                "pdf_url": "https://example.com/clean-code.pdf",
                "total_chapters": 15
            },
            {
                "title": "Atomic Habits",
                "pdf_url": "https://example.com/atomic-habits.pdf",
                "total_chapters": 12
            }
        ]
        
        for book_data in queued_books:
            existing = db.query(Book).filter(
                Book.title == book_data["title"],
                Book.status == "queued"
            ).first()
            
            if not existing:
                queued_book = Book(
                    title=book_data["title"],
                    pdf_url=book_data["pdf_url"],
                    status="queued",
                    total_chapters=book_data["total_chapters"]
                )
                db.add(queued_book)
                print(f"   ✅ Queued: {book_data['title']}")
            else:
                print(f"   ⚠️  Already queued: {book_data['title']}")
        
        # 6. Create Past Book
        print("📚 Creating past book...")
        existing_past = db.query(Book).filter(
            Book.title == "Thinking, Fast and Slow",
            Book.status == "completed"
        ).first()
        
        if not existing_past:
            past_book = Book(
                title="Thinking, Fast and Slow",
                pdf_url="https://example.com/thinking-fast-slow.pdf",
                status="completed",
                total_chapters=8,
                completed_date=datetime(2024, 11, 15)
            )
            db.add(past_book)
            print("   ✅ Past book: Thinking, Fast and Slow")
        else:
            print("   ⚠️  Past book already exists")
        
        # 7. Create Meeting
        print("📅 Creating meeting...")
        existing_meeting = db.query(Meeting).first()
        if not existing_meeting:
            meeting = Meeting(
                date="December 15, 2024",
                time="7:00 PM EAT",
                meet_link="https://meet.google.com/abc-defg-hij"
            )
            db.add(meeting)
            print("   ✅ Meeting scheduled for December 15, 2024")
        else:
            print(f"   ⚠️  Meeting already exists: {existing_meeting.date}")
        
        # Commit all changes
        db.commit()
        print("\n🎉 Database seeded successfully!\n")
        
        # Print summary
        print("=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Access Code:   TW2024DEC")
        print(f"Admin Email:   admin@bookclub.com")
        print(f"Admin Pass:    admin123")
        print(f"Test Email:    test@example.com")
        print(f"Test Pass:     password123")
        print("=" * 50)
        print("\n✅ You can now run the application!")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()