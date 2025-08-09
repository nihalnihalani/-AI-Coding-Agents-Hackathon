from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        self.algorithm = settings.jwt_algorithm
        self.secret_key = settings.jwt_secret_key
        self.access_token_expire_minutes = settings.jwt_expire_minutes
        
        # In-memory user store (would be database in production)
        self.users_db = {
            "demo@aura.ai": {
                "user_id": "user_123",
                "email": "demo@aura.ai",
                "hashed_password": self._hash_password("demo123"),
                "full_name": "Demo User",
                "role": "employee",
                "is_active": True,
                "permissions": ["onboarding:read", "onboarding:write", "chat:access"]
            },
            "admin@aura.ai": {
                "user_id": "admin_456",
                "email": "admin@aura.ai",
                "hashed_password": self._hash_password("admin123"),
                "full_name": "Admin User",
                "role": "admin",
                "is_active": True,
                "permissions": ["*"]  # All permissions
            },
            "manager@aura.ai": {
                "user_id": "manager_789",
                "email": "manager@aura.ai",
                "hashed_password": self._hash_password("manager123"),
                "full_name": "Manager User",
                "role": "manager",
                "is_active": True,
                "permissions": [
                    "onboarding:read", "onboarding:write", "onboarding:approve",
                    "chat:access", "approvals:manage", "users:view"
                ]
            }
        }
        
        # API key store (for service-to-service authentication)
        self.api_keys = {
            "aura_service_key_123": {
                "name": "Aura Internal Service",
                "permissions": ["system:internal"],
                "created_at": datetime.now().isoformat(),
                "is_active": True
            }
        }
    
    def _hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password."""
        try:
            user = self.users_db.get(email)
            if not user:
                return None
            
            if not self._verify_password(password, user["hashed_password"]):
                return None
            
            if not user.get("is_active", False):
                return None
            
            # Remove sensitive data before returning
            user_data = user.copy()
            del user_data["hashed_password"]
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error authenticating user {email}: {e}")
            return None
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        try:
            to_encode = data.copy()
            
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            
            to_encode.update({"exp": expire, "iat": datetime.utcnow()})
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key for service-to-service authentication."""
        try:
            key_data = self.api_keys.get(api_key)
            if not key_data or not key_data.get("is_active", False):
                return None
            
            return key_data
            
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return None
    
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission."""
        try:
            # Admin wildcard permission
            if "*" in user_permissions:
                return True
            
            # Exact permission match
            if required_permission in user_permissions:
                return True
            
            # Wildcard permission matching (e.g., "onboarding:*" matches "onboarding:read")
            for permission in user_permissions:
                if permission.endswith(":*"):
                    permission_prefix = permission[:-1]  # Remove the "*"
                    if required_permission.startswith(permission_prefix):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking permission {required_permission}: {e}")
            return False

# Global auth service instance
auth_service = AuthService()

# Dependency functions for FastAPI

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = auth_service.verify_token(token)
        
        if payload is None:
            raise credentials_exception
        
        # Get user email from token
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        # Get user data
        user = auth_service.users_db.get(email)
        if user is None:
            raise credentials_exception
        
        # Remove sensitive data
        user_data = user.copy()
        del user_data["hashed_password"]
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise credentials_exception

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current active user."""
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        
        if not auth_service.check_permission(user_permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}"
            )
        
        return current_user
    
    return permission_checker

def require_role(role: str):
    """Decorator to require specific role."""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "")
        
        if user_role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}"
            )
        
        return current_user
    
    return role_checker

# API Key authentication
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Verify API key for service-to-service authentication."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        api_key = credentials.credentials
        key_data = auth_service.verify_api_key(api_key)
        
        if key_data is None:
            raise credentials_exception
        
        return key_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying API key: {e}")
        raise credentials_exception

# Optional authentication (for public endpoints that can benefit from user context)
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[Dict[str, Any]]:
    """Get user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = auth_service.verify_token(token)
        
        if payload is None:
            return None
        
        email = payload.get("sub")
        if email is None:
            return None
        
        user = auth_service.users_db.get(email)
        if user is None or not user.get("is_active", False):
            return None
        
        # Remove sensitive data
        user_data = user.copy()
        del user_data["hashed_password"]
        
        return user_data
        
    except Exception as e:
        logger.warning(f"Optional authentication failed: {e}")
        return None

# Session-based authentication for WebSocket connections
def verify_websocket_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify token for WebSocket authentication."""
    try:
        payload = auth_service.verify_token(token)
        if payload is None:
            return None
        
        email = payload.get("sub")
        if email is None:
            return None
        
        user = auth_service.users_db.get(email)
        if user is None or not user.get("is_active", False):
            return None
        
        # Remove sensitive data
        user_data = user.copy()
        del user_data["hashed_password"]
        
        return user_data
        
    except Exception as e:
        logger.error(f"WebSocket token verification failed: {e}")
        return None