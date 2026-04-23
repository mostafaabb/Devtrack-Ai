"""
Notification model for real-time alerts and messages to business staff.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.session import Base


class Notification(Base):
    """
    Notification for business staff (new order, new message, etc.).
    """
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Null = all users
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info")  # info, warning, success, error
    
    # Reference to related entity
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(255), nullable=True)
    
    is_read = Column(Boolean, default=False)
    extra_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"
