"""
Customer model - represents end customers who interact with businesses.
Tracks customer profiles, chat history, orders, and bookings.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.session import Base


class Customer(Base):
    """
    Customer model - the end-user who interacts with a business.
    Each customer belongs to a specific business (multi-tenant).
    """
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Customer info
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True, index=True)
    
    # Channel they came from (whatsapp, web, instagram)
    channel = Column(String(50), default="web")
    channel_id = Column(String(255), nullable=True)  # WhatsApp number, etc.
    
    # Profile data
    avatar_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # Tags for segmentation: ["vip", "frequent"]
    extra_data = Column(JSON, default=dict)  # Extra data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="customers")
    conversations = relationship("Conversation", back_populates="customer")
    orders = relationship("Order", back_populates="customer")
    bookings = relationship("Booking", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.name or self.phone}>"
