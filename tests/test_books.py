"""
Test book-related endpoints
"""
import pytest
from app.models import BookSuggestion, ReadingProgress

class TestCurrentBook:
    """Test current book endpoint"""
    
    def test_get_current_book_with_code(self, client, access_code, current_book, meeting):
        """Test getting current book with verified code"""
        # Verify code first
        client.post("/auth/verify-code", data={"code": "TEST2024"})
        
        response = client.get("/api/books/current")
        assert response.status_code == 200
        data = response.json()
        assert data["book"]["title"] == "Test Book"
        assert data["meeting"]["date"] == "December 20, 2024"
    
    def test_get_current_book_without_access(self, client, current_book):
        """Test that current book requires access"""
        response = client.get("/api/books/current")
        assert response.status_code == 403
    
    def test_get_current_book_authenticated(self, client, test_user, current_book):
        """Test getting current book when authenticated"""
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        response = client.get("/api/books/current")
        assert response.status_code == 200

class TestBookQueue:
    """Test queued books"""
    
    def test_get_queued_books(self, client, access_code, queued_book):
        """Test getting queued books"""
        client.post("/auth/verify-code", data={"code": "TEST2024"})
        
        response = client.get("/api/books/queue")
        assert response.status_code == 200
        books = response.json()
        assert len(books) == 1
        assert books[0]["title"] == "Queued Book"
        assert books[0]["status"] == "queued"

class TestBookSuggestions:
    """Test book suggestions"""
    
    def test_submit_suggestion_authenticated(self, client, test_user):
        """Test submitting a book suggestion"""
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        response = client.post(
            "/api/books/suggestions",
            json={
                "title": "Atomic Habits",
                "pdf_url": "https://example.com/atomic.pdf"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Atomic Habits"
        assert data["status"] == "pending"
    
    def test_submit_suggestion_unauthenticated(self, client):
        """Test that suggestions require authentication"""
        response = client.post(
            "/api/books/suggestions",
            json={
                "title": "Test Book",
                "pdf_url": "https://example.com/test.pdf"
            }
        )
        assert response.status_code == 401
    
    def test_get_my_suggestions(self, client, test_user, db):
        """Test getting user's own suggestions"""
        # Login
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Create some suggestions
        suggestion1 = BookSuggestion(
            title="Book 1",
            pdf_url="https://example.com/1.pdf",
            user_id=test_user.id,
            status="pending"
        )
        suggestion2 = BookSuggestion(
            title="Book 2",
            pdf_url="https://example.com/2.pdf",
            user_id=test_user.id,
            status="approved"
        )
        db.add_all([suggestion1, suggestion2])
        db.commit()
        
        # Get suggestions
        response = client.get("/api/books/suggestions/my")
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions) == 2
        assert suggestions[0]["title"] in ["Book 1", "Book 2"]

class TestReadingProgress:
    """Test reading progress tracking"""
    
    def test_update_progress(self, client, test_user, current_book):
        """Test updating reading progress"""
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        response = client.put(
            "/api/books/progress",
            json={
                "book_id": current_book.id,
                "chapter": 3
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["chapter"] == 3
        assert data["book_id"] == current_book.id
    
    def test_update_progress_multiple_times(self, client, test_user, current_book):
        """Test updating progress multiple times (should update, not create new)"""
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # First update
        client.put("/api/books/progress", json={
            "book_id": current_book.id,
            "chapter": 3
        })
        
        # Second update
        response = client.put("/api/books/progress", json={
            "book_id": current_book.id,
            "chapter": 5
        })
        
        assert response.status_code == 200
        assert response.json()["chapter"] == 5
    
    def test_get_my_progress(self, client, test_user, current_book, db):
        """Test getting user's progress"""
        # Create progress
        progress = ReadingProgress(
            user_id=test_user.id,
            book_id=current_book.id,
            chapter=4
        )
        db.add(progress)
        db.commit()
        
        # Login and get progress
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        response = client.get("/api/books/progress/my")
        assert response.status_code == 200
        data = response.json()
        assert data["progress"]["chapter"] == 4
    
    def test_community_progress(self, client, access_code, current_book, test_user, db):
        """Test getting community progress stats"""
        # Create some progress data
        progress1 = ReadingProgress(
            user_id=test_user.id,
            book_id=current_book.id,
            chapter=2
        )
        db.add(progress1)
        db.commit()
        
        # Verify code and get stats
        client.post("/auth/verify-code", data={"code": "TEST2024"})
        
        response = client.get("/api/books/progress/community")
        assert response.status_code == 200
        data = response.json()
        assert data["total_members"] == 1
        assert len(data["stats"]) > 0