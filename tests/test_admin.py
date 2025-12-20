"""
Test admin endpoints
"""
import pytest
from app.models import BookSuggestion, Book

class TestAdminAccessControl:
    """Test admin access control"""
    
    def test_admin_endpoint_requires_auth(self, client):
        """Test that admin endpoints require authentication"""
        response = client.get("/api/admin/stats")
        assert response.status_code == 401
    
    def test_admin_endpoint_requires_admin_role(self, client, test_user):
        """Test that admin endpoints require admin role"""
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        response = client.get("/api/admin/stats")
        assert response.status_code == 403
    
    def test_admin_endpoint_allows_admin(self, client, admin_user):
        """Test that admin can access admin endpoints"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.get("/api/admin/stats")
        assert response.status_code == 200

class TestAccessCodeManagement:
    """Test access code management"""
    
    def test_get_access_code(self, client, admin_user, access_code):
        """Test getting current access code"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.get("/api/admin/code")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "TEST2024"
    
    def test_update_access_code(self, client, admin_user, access_code):
        """Test updating access code"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.put(
            "/api/admin/code",
            json={"new_code": "NEW2024"}
        )
        assert response.status_code == 200
        assert "NEW2024" in response.json()["message"]

class TestBookManagement:
    """Test book management"""
    
    def test_update_current_book(self, client, admin_user, current_book):
        """Test updating current book details"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.put(
            "/api/admin/books/current",
            json={
                "title": "Updated Title",
                "current_chapters": "Chapters 3-4"
            }
        )
        assert response.status_code == 200
    
    def test_complete_current_book(self, client, admin_user, current_book, db):
        """Test marking current book as completed"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.post("/api/admin/books/complete")
        assert response.status_code == 200
        
        # Verify book status changed
        db.refresh(current_book)
        assert current_book.status == "completed"
        assert current_book.completed_date is not None
    
    def test_set_queued_book_as_current(self, client, admin_user, queued_book, db):
        """Test setting a queued book as current"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.post(
            f"/api/admin/books/{queued_book.id}/set-current",
            json={"current_chapters": "Chapters 1-2"}
        )
        assert response.status_code == 200
        
        # Verify book status changed
        db.refresh(queued_book)
        assert queued_book.status == "current"
        assert queued_book.current_chapters == "Chapters 1-2"

class TestSuggestionManagement:
    """Test book suggestion management"""
    
    def test_get_pending_suggestions(self, client, admin_user, test_user, db):
        """Test getting pending suggestions"""
        # Create a pending suggestion
        suggestion = BookSuggestion(
            title="Test Suggestion",
            pdf_url="https://example.com/test.pdf",
            user_id=test_user.id,
            status="pending"
        )
        db.add(suggestion)
        db.commit()
        
        # Login as admin and get suggestions
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.get("/api/admin/suggestions/pending")
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions) == 1
        assert suggestions[0]["title"] == "Test Suggestion"
    
    def test_approve_suggestion(self, client, admin_user, test_user, db):
        """Test approving a book suggestion"""
        # Create a pending suggestion
        suggestion = BookSuggestion(
            title="Approved Book",
            pdf_url="https://example.com/approved.pdf",
            user_id=test_user.id,
            status="pending"
        )
        db.add(suggestion)
        db.commit()
        suggestion_id = suggestion.id
        
        # Login as admin
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        # Approve suggestion
        response = client.put(f"/api/admin/suggestions/{suggestion_id}/approve")
        assert response.status_code == 200
        
        # Verify suggestion status changed
        db.refresh(suggestion)
        assert suggestion.status == "approved"
        
        # Verify book was added to queue
        queued_book = db.query(Book).filter(
            Book.title == "Approved Book",
            Book.status == "queued"
        ).first()
        assert queued_book is not None
    
    def test_reject_suggestion(self, client, admin_user, test_user, db):
        """Test rejecting a book suggestion"""
        # Create a pending suggestion
        suggestion = BookSuggestion(
            title="Rejected Book",
            pdf_url="https://example.com/rejected.pdf",
            user_id=test_user.id,
            status="pending"
        )
        db.add(suggestion)
        db.commit()
        suggestion_id = suggestion.id
        
        # Login as admin
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        # Reject suggestion
        response = client.put(f"/api/admin/suggestions/{suggestion_id}/reject")
        assert response.status_code == 200
        
        # Verify suggestion status changed
        db.refresh(suggestion)
        assert suggestion.status == "rejected"

class TestMeetingManagement:
    """Test meeting management"""
    
    def test_update_meeting(self, client, admin_user, meeting):
        """Test updating meeting details"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.put(
            "/api/admin/meeting",
            json={
                "date": "January 5, 2025",
                "time": "8:00 PM EAT",
                "meet_link": "https://meet.google.com/new"
            }
        )
        assert response.status_code == 200

class TestAdminStats:
    """Test admin statistics"""
    
    def test_get_admin_stats(self, client, admin_user, test_user, current_book, db):
        """Test getting admin dashboard stats"""
        client.post("/auth/login", data={
            "email": "admin@example.com",
            "password": "admin123"
        })
        
        response = client.get("/api/admin/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_members" in data
        assert "new_members_this_month" in data
        assert "pending_suggestions" in data
        assert "current_book_engagement" in data
        
        # Should have at least 2 users (admin + test_user)
        assert data["total_members"] >= 2