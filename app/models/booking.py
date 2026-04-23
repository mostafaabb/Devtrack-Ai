"""
Booking model.
Supports reservations for restaurants, hotels, clinics, and services.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Enum as SQLEnum, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class BookingStatus(str, enum.Enum):
    """Booking lifecycle status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class BookingType(str, enum.Enum):
    """Type of booking."""
    TABLE = "table"           # Restaurant table
    ROOM = "room"             # Hotel room
    APPOINTMENT = "appointment"  # Clinic/service appointment
    SERVICE = "service"       # General service booking


class Booking(Base):
    """
    Booking/Reservation model supporting multiple industry types.
    Can be created via AI chat, manually, or through API.
    """
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    
    # Booking details
    booking_number = Column(String(50), unique=True, nullable=False)
    booking_type = Column(SQLEnum(BookingType), default=BookingType.SERVICE)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING)
    
    # Schedule
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Details
    party_size = Column(Integer, default=1)  # Number of guests
    resource_name = Column(String(255), nullable=True)  # Room name, table number, etc.
    service_name = Column(String(255), nullable=True)   # Service or procedure name
    
    # Pricing
    price = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    
    # Source tracking
    source = Column(String(50), default="manual")  # manual, ai_chat, whatsapp, web
    conversation_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Extra data
    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")

    def __repr__(self):
        return f"<Booking {self.booking_number} - {self.status}>"
