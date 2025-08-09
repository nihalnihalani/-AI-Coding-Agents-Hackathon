import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.core.auth import auth_service, verify_websocket_token


class TestAuthentication:
    """Test authentication system functionality."""
    
    def test_login_success(self, client: TestClient):
        """Test successful login with valid credentials."""
        response = client.post("/auth/login", json={
            "email": "demo@aura.ai",
            "password": "demo123"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["access_token"] is not None
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user_info"]["email"] == "demo@aura.ai"
        assert data["user_info"]["role"] == "employee"
        assert "onboarding:read" in data["user_info"]["permissions"]
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        response = client.post("/auth/login", json={
            "email": "demo@aura.ai",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@aura.ai",
            "password": "password123"
        })
        
        assert response.status_code == 401
    
    def test_oauth2_token_endpoint(self, client: TestClient):
        """Test OAuth2 compatible token endpoint."""
        response = client.post("/auth/token", data={
            "username": "admin@aura.ai",
            "password": "admin123",
            "grant_type": "password"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["access_token"] is not None
        assert data["user_info"]["role"] == "admin"
        assert "*" in data["user_info"]["permissions"]  # Admin has all permissions
    
    def test_get_current_user(self, client: TestClient, auth_headers):
        """Test getting current user information."""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "demo@aura.ai"
        assert data["role"] == "employee"
        assert data["is_active"] is True
    
    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_refresh_token(self, client: TestClient, auth_headers):
        """Test token refresh functionality."""
        response = client.post("/auth/refresh", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["access_token"] is not None
        assert data["token_type"] == "bearer"
        assert "refreshed successfully" in data["message"]
    
    def test_logout(self, client: TestClient, auth_headers):
        """Test user logout."""
        response = client.post("/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "Logged out successfully" in data["message"]
    
    def test_change_password(self, client: TestClient, auth_headers):
        """Test password change functionality."""
        # First, change password
        response = client.post("/auth/change-password", 
            headers=auth_headers,
            json={
                "current_password": "demo123",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 200
        
        # Verify old password doesn't work
        login_response = client.post("/auth/login", json={
            "email": "demo@aura.ai",
            "password": "demo123"
        })
        assert login_response.status_code == 401
        
        # Verify new password works
        login_response = client.post("/auth/login", json={
            "email": "demo@aura.ai",
            "password": "newpassword123"
        })
        assert login_response.status_code == 200
        
        # Reset password back to original for other tests
        new_token = login_response.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}
        
        reset_response = client.post("/auth/change-password",
            headers=new_headers,
            json={
                "current_password": "newpassword123",
                "new_password": "demo123"
            }
        )
        assert reset_response.status_code == 200
    
    def test_change_password_wrong_current(self, client: TestClient, auth_headers):
        """Test password change with wrong current password."""
        response = client.post("/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]
    
    def test_get_permissions(self, client: TestClient, auth_headers):
        """Test getting user permissions."""
        response = client.get("/auth/permissions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role"] == "employee"
        assert "onboarding:read" in data["permissions"]
        assert data["has_admin_access"] is False
        assert "permission_categories" in data
    
    def test_admin_permissions(self, client: TestClient, admin_headers):
        """Test admin user permissions."""
        response = client.get("/auth/permissions", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role"] == "admin"
        assert "*" in data["permissions"]
        assert data["has_admin_access"] is True
    
    def test_get_demo_users(self, client: TestClient):
        """Test getting demo users list."""
        response = client.get("/auth/demo-users")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["demo_users"]) == 3  # demo, admin, manager
        assert data["warning"] == "In production, this endpoint should be removed"
        
        # Check that all demo users are present
        emails = [user["email"] for user in data["demo_users"]]
        assert "demo@aura.ai" in emails
        assert "admin@aura.ai" in emails
        assert "manager@aura.ai" in emails
    
    def test_validate_token(self, client: TestClient, auth_headers):
        """Test token validation endpoint."""
        response = client.get("/auth/validate-token", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["email"] == "demo@aura.ai"
        assert "Token is valid" in data["message"]
    
    def test_auth_health_check(self, client: TestClient):
        """Test authentication service health check."""
        response = client.get("/auth/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["auth_service"] == "operational"
        assert data["user_count"] == 3  # demo, admin, manager
        assert data["jwt_algorithm"] == "HS256"
    
    def test_expired_token(self, client: TestClient):
        """Test behavior with expired token."""
        # Create an expired token
        expired_token = auth_service.create_access_token(
            data={"sub": "demo@aura.ai", "role": "employee"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_invalid_token_format(self, client: TestClient):
        """Test behavior with invalid token format."""
        headers = {"Authorization": "Bearer invalid-token-format"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_websocket_token_verification(self):
        """Test WebSocket token verification."""
        # Get valid token
        user = auth_service.authenticate_user("demo@aura.ai", "demo123")
        token = auth_service.create_access_token(
            data={"sub": user["email"], "role": user["role"]}
        )
        
        # Verify token works for WebSocket
        verified_user = verify_websocket_token(token)
        assert verified_user is not None
        assert verified_user["email"] == "demo@aura.ai"
        
        # Test invalid token
        invalid_user = verify_websocket_token("invalid-token")
        assert invalid_user is None
    
    def test_role_based_access_control(self, client: TestClient):
        """Test role-based access control across different user types."""
        # Test employee permissions
        employee_response = client.post("/auth/login", json={
            "email": "demo@aura.ai",
            "password": "demo123"
        })
        employee_token = employee_response.json()["access_token"]
        employee_headers = {"Authorization": f"Bearer {employee_token}"}
        
        # Test manager permissions
        manager_response = client.post("/auth/login", json={
            "email": "manager@aura.ai",  
            "password": "manager123"
        })
        manager_token = manager_response.json()["access_token"]
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Test admin permissions
        admin_response = client.post("/auth/login", json={
            "email": "admin@aura.ai",
            "password": "admin123"
        })
        admin_token = admin_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Verify different permission levels
        employee_perms = client.get("/auth/permissions", headers=employee_headers).json()
        manager_perms = client.get("/auth/permissions", headers=manager_headers).json()
        admin_perms = client.get("/auth/permissions", headers=admin_headers).json()
        
        # Employee should have basic permissions only
        assert employee_perms["role"] == "employee"
        assert "onboarding:read" in employee_perms["permissions"]
        assert employee_perms["has_admin_access"] is False
        
        # Manager should have additional permissions
        assert manager_perms["role"] == "manager"
        assert "approvals:manage" in manager_perms["permissions"]
        assert "users:view" in manager_perms["permissions"]
        
        # Admin should have all permissions
        assert admin_perms["role"] == "admin"
        assert "*" in admin_perms["permissions"]
        assert admin_perms["has_admin_access"] is True