"""
Audit Log model — Tracks all significant actions performed by users.
Provides an immutable activity trail for compliance and debugging.
"""
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.db.session import Base


class AuditLog(Base):
    """
    Immutable audit trail of user/system actions.
    
    Examples:
    - user.login, user.register, user.password_change
    - order.created, order.status_changed
    - booking.created, booking.cancelled
    - product.created, product.updated, product.deleted
    - settings.updated, whatsapp.connected
    - workflow.executed, document.uploaded
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Who
    business_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    
    # What
    action = Column(String(100), nullable=False, index=True)  # e.g., "order.created"
    entity_type = Column(String(50), nullable=True)  # e.g., "order"
    entity_id = Column(String(100), nullable=True)   # UUID of the entity
    
    # Details
    description = Column(Text, nullable=True)
    old_values = Column(JSON, nullable=True)  # Previous state
    new_values = Column(JSON, nullable=True)  # New state
    metadata_extra = Column(JSON, nullable=True)  # Additional context
    
    # Where
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # When
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_email} at {self.created_at}>"


class StaffInvitation(Base):
    """
    Staff invitation tokens for inviting team members.
    """
    __tablename__ = "staff_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    role = Column(String(50), default="staff")
    invited_by = Column(UUID(as_uuid=True), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    
    is_accepted = Column(String(20), default="pending")  # pending, accepted, expired
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<StaffInvitation {self.email} for business {self.business_id}>"
