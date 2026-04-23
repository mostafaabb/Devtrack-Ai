"""
Pydantic schemas for authentication and user management.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    business_name: str
    business_type: str = "general"
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_api_token: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """Schema for user response."""
    id: UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    business_id: Optional[UUID] = None
    is_active: bool
    is_verified: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
