"""
User model - handles authentication and role-based access.
Supports multi-tenant architecture where each user belongs to a business.
Includes: login attempt tracking, email verification, password reset tokens.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class UserRole(str, enum.Enum):
    """User roles within a business."""
    ADMIN = "admin"              # Business owner with full access
    STAFF = "staff"              # Staff member with limited access
    SUPER_ADMIN = "super_admin"  # Platform-level admin


class User(Base):
    """
    User model for authentication and authorization.
    Each user belongs to a business (multi-tenant).
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.STAFF, nullable=False)
    
    # Multi-tenant: link user to business
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Email verification
    verification_code = Column(String(10), nullable=True)
    verification_code_expires = Column(DateTime, nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # Security: login attempt tracking
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="users")

    def __repr__(self):
        return f"<User {self.email}>"

    @property
    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
