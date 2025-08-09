from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta

from ..core.auth import auth_service, get_current_active_user
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Request/Response models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: dict

class UserInfo(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    role: str
    permissions: list
    is_active: bool

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Authenticate user and return access token."""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
        access_token = auth_service.create_access_token(
            data={"sub": user["email"], "role": user["role"]},
            expires_delta=access_token_expires
        )
        
        logger.info(f"User {user['email']} logged in successfully")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.access_token_expire_minutes * 60,  # Convert to seconds
            "user_info": {
                "user_id": user["user_id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "permissions": user["permissions"],
                "is_active": user["is_active"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token endpoint."""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(form_data.username, form_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
        access_token = auth_service.create_access_token(
            data={"sub": user["email"], "role": user["role"]},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.access_token_expire_minutes * 60,
            "user_info": {
                "user_id": user["user_id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "permissions": user["permissions"],
                "is_active": user["is_active"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token generation failed"
        )

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user information."""
    return UserInfo(
        user_id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        permissions=current_user["permissions"],
        is_active=current_user["is_active"]
    )

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_active_user)):
    """Refresh access token."""
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
        access_token = auth_service.create_access_token(
            data={"sub": current_user["email"], "role": current_user["role"]},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.access_token_expire_minutes * 60,
            "message": "Token refreshed successfully"
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_active_user)):
    """Logout user (client should discard token)."""
    try:
        logger.info(f"User {current_user['email']} logged out")
        
        return {
            "message": "Logged out successfully",
            "user_id": current_user["user_id"]
        }
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Change user password."""
    try:
        # Verify current password
        current_hashed = auth_service.users_db[current_user["email"]]["hashed_password"]
        
        if not auth_service._verify_password(password_data.current_password, current_hashed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        new_hashed = auth_service._hash_password(password_data.new_password)
        auth_service.users_db[current_user["email"]]["hashed_password"] = new_hashed
        
        logger.info(f"Password changed for user {current_user['email']}")
        
        return {
            "message": "Password changed successfully",
            "user_id": current_user["user_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.get("/permissions")
async def get_user_permissions(current_user: dict = Depends(get_current_active_user)):
    """Get current user's permissions."""
    return {
        "user_id": current_user["user_id"],
        "role": current_user["role"],
        "permissions": current_user["permissions"],
        "has_admin_access": "*" in current_user["permissions"],
        "permission_categories": _categorize_permissions(current_user["permissions"])
    }

@router.get("/demo-users")
async def get_demo_users():
    """Get available demo users for testing (development only)."""
    try:
        demo_users = []
        
        for email, user_data in auth_service.users_db.items():
            demo_users.append({
                "email": email,
                "role": user_data["role"],
                "full_name": user_data["full_name"],
                "permissions": user_data["permissions"],
                "password_hint": "Check the source code for demo passwords"
            })
        
        return {
            "demo_users": demo_users,
            "note": "These are demo users for testing purposes only",
            "warning": "In production, this endpoint should be removed"
        }
        
    except Exception as e:
        logger.error(f"Error getting demo users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve demo users"
        )

@router.get("/validate-token")
async def validate_token(current_user: dict = Depends(get_current_active_user)):
    """Validate if current token is still valid."""
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "message": "Token is valid"
    }

@router.get("/health")
async def auth_health():
    """Check authentication service health."""
    try:
        # Check if auth service is working
        test_user_count = len(auth_service.users_db)
        test_api_key_count = len(auth_service.api_keys)
        
        return {
            "status": "healthy",
            "auth_service": "operational",
            "user_count": test_user_count,
            "api_key_count": test_api_key_count,
            "jwt_algorithm": auth_service.algorithm,
            "token_expires_minutes": auth_service.access_token_expire_minutes
        }
        
    except Exception as e:
        logger.error(f"Auth health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unhealthy"
        )

# Helper functions

def _categorize_permissions(permissions: list) -> dict:
    """Categorize permissions by domain."""
    categories = {
        "onboarding": [],
        "chat": [],
        "approvals": [],
        "users": [],
        "system": [],
        "other": []
    }
    
    for permission in permissions:
        if permission == "*":
            categories["system"].append("admin_access")
            continue
        
        if ":" in permission:
            domain = permission.split(":")[0]
            if domain in categories:
                categories[domain].append(permission)
            else:
                categories["other"].append(permission)
        else:
            categories["other"].append(permission)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}