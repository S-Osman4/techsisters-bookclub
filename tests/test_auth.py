"""
Test authentication endpoints
"""
import pytest
from app.models import User

class TestCodeVerification:
    """Test access code verification"""
    
    def test_verify_valid_code(self, client, access_code):
        """Test verifying a valid access code"""
        response = client.post(
            "/auth/verify-code",
            data={"code": "TEST2024"}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        assert "verified" in response.json()["message"].lower()
    
    def test_verify_invalid_code(self, client, access_code):
        """Test verifying an invalid access code"""
        response = client.post(
            "/auth/verify-code",
            data={"code": "WRONG"}
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    
    def test_verify_code_case_insensitive(self, client, access_code):
        """Test that code verification is case-insensitive"""
        response = client.post(
            "/auth/verify-code",
            data={"code": "test2024"}  # lowercase
        )
        assert response.status_code == 200
        assert response.json()["success"] == True

class TestUserRegistration:
    """Test user registration"""
    
    def test_register_with_valid_code(self, client, access_code):
        """Test registering a new user with valid code"""
        # First verify code
        client.post("/auth/verify-code", data={"code": "TEST2024"})
        
        # Then register
        response = client.post(
            "/auth/register",
            data={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert data["is_admin"] == False
    
    def test_register_without_code_verification(self, client):
        """Test that registration fails without code verification"""
        response = client.post(
            "/auth/register",
            data={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 403
        assert "code" in response.json()["detail"].lower()
    
    def test_register_duplicate_email(self, client, access_code, test_user):
        """Test that duplicate email registration fails"""
        client.post("/auth/verify-code", data={"code": "TEST2024"})
        
        response = client.post(
            "/auth/register",
            data={
                "name": "Another User",
                "email": "test@example.com",  # Already exists
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_short_password(self, client, access_code):
        """Test that short passwords are rejected"""
        client.post("/auth/verify-code", data={"code": "TEST2024"})
        
        response = client.post(
            "/auth/register",
            data={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "short"  # Too short
            }
        )
        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"].lower()

class TestUserLogin:
    """Test user login"""
    
    def test_login_valid_credentials(self, client, test_user):
        """Test login with valid credentials"""
        response = client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        assert "welcome" in response.json()["message"].lower()
    
    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email"""
        response = client.post(
            "/auth/login",
            data={
                "email": "nonexistent@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_login_case_insensitive_email(self, client, test_user):
        """Test that email login is case-insensitive"""
        response = client.post(
            "/auth/login",
            data={
                "email": "TEST@EXAMPLE.COM",  # Uppercase
                "password": "password123"
            }
        )
        assert response.status_code == 200

class TestAuthStatus:
    """Test authentication status checks"""
    
    def test_get_current_user_authenticated(self, client, test_user):
        """Test getting current user info when authenticated"""
        # Login first
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        response = client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
    
    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user when not authenticated"""
        response = client.get("/auth/me")
        assert response.status_code == 401
    
    def test_logout(self, client, test_user):
        """Test logout functionality"""
        # Login first
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Then logout
        response = client.post("/auth/logout")
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify can't access protected route
        response = client.get("/auth/me")
        assert response.status_code == 401