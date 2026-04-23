"""
Common schemas used across the platform.
Provides pagination, standardized responses, and shared models.
"""
from pydantic import BaseModel, Field
from typing import List, Any, Optional, Generic, TypeVar
from datetime import datetime


T = TypeVar("T")


class PaginatedResponse(BaseModel):
    """Standardized paginated response with metadata."""
    items: List[Any]
    total: int = Field(description="Total number of items matching the query")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there's a next page")
    has_previous: bool = Field(description="Whether there's a previous page")


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: str
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    description: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StaffInviteRequest(BaseModel):
    """Request to invite a staff member."""
    email: str
    role: str = "staff"


class StaffInviteAccept(BaseModel):
    """Accept a staff invitation."""
    token: str
    full_name: str
    password: str
    phone: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Request password reset."""
    email: str


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token."""
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    """Change password (authenticated)."""
    current_password: str
    new_password: str


class ExportRequest(BaseModel):
    """Data export request."""
    entity_type: str = Field(description="Type: customers, orders, bookings, products, conversations")
    format: str = Field(default="csv", description="Format: csv")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SubscriptionInfo(BaseModel):
    """Current subscription plan information."""
    plan: str
    limits: dict
    usage: dict
    is_over_limit: bool
    upgrade_required: List[str] = []
