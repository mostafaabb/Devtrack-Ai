"""
JWT Authentication, password security, and user authentication.
Includes: password hashing, strength validation, JWT tokens, refresh tokens,
account lockout, and audit logging.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import re
import secrets
import bcrypt
import logging

logger = logging.getLogger("devtrack.security")

# HTTP Bearer security scheme
security = HTTPBearer()


# ─── Password Utilities ──────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    # bcrypt has a 72-byte limit, so we hash the password first with SHA-256
    # then use that hash as input to bcrypt
    import hashlib
    
    # First, create a SHA-256 hash of the password
    password_hash = hashlib.sha256(password.encode('utf-8')).digest()
    
    # Then hash that with bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_hash, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password."""
    import hashlib
    
    try:
        # First, create a SHA-256 hash of the plain password
        password_hash = hashlib.sha256(plain_password.encode('utf-8')).digest()
        
        # Then verify against the stored bcrypt hash
        return bcrypt.checkpw(password_hash, hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def validate_password_strength(password: str) -> dict:
    """
    Validate password meets strength requirements.
    
    Returns:
        {"valid": True/False, "errors": [...]}
    """
    errors = []
    
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>?/~`]", password):
        errors.append("Password must contain at least one special character")
    
    return {"valid": len(errors) == 0, "errors": errors}


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


def generate_secure_token() -> str:
    """Generate a secure random token for password reset, invitations, etc."""
    return secrets.token_urlsafe(48)


# ─── JWT Token Management ─────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token (longer-lived).
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> dict:
    """
    Decode and verify a JWT refresh token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type — expected refresh token",
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


# ─── Authentication Dependencies ──────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency to extract and validate the current user from JWT token.
    """
    import uuid as uuid_pkg
    token = credentials.credentials
    payload = decode_access_token(token)
    
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Try to convert string IDs to UUID objects for database compatibility
    try:
        user_id = uuid_pkg.UUID(user_id_raw)
    except (ValueError, TypeError, AttributeError):
        user_id = user_id_raw
        
    business_id_raw = payload.get("business_id")
    try:
        business_id = uuid_pkg.UUID(business_id_raw) if business_id_raw else None
    except (ValueError, TypeError, AttributeError):
        business_id = business_id_raw

    return {
        "user_id": user_id,
        "business_id": business_id,
        "role": payload.get("role"),
        "email": payload.get("email"),
    }


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires the user to be an admin."""
    if current_user.get("role") not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_super_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires the user to be a super admin."""
    if current_user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


# ─── Audit Logger ──────────────────────────────────────────────────

def log_audit(
    db, action: str, user_id=None, business_id=None, user_email=None, 
    entity_type=None, entity_id=None, description=None, 
    old_values=None, new_values=None, ip_address=None, user_agent=None
):
    """
    Create an audit log entry. Handles both UUID objects and strings.
    """
    import uuid as uuid_pkg
    try:
        from app.models.audit import AuditLog
        
        # Ensure IDs are UUID objects if they are strings
        if isinstance(user_id, str) and user_id:
            try:
                user_id = uuid_pkg.UUID(user_id)
            except (ValueError, AttributeError):
                pass
        
        if isinstance(business_id, str) and business_id:
            try:
                business_id = uuid_pkg.UUID(business_id)
            except (ValueError, AttributeError):
                pass

        log = AuditLog(
            action=action,
            user_id=user_id,
            business_id=business_id,
            user_email=user_email,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        # Don't commit here — let the caller handle the transaction
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")
        logger.warning(f"Audit log data: action={action}, user_id={user_id}, business_id={business_id}")
