"""
Business model - represents a business/tenant in the multi-tenant system.
Each business can enable different industry modules.
Sensitive fields (API tokens, payment keys) are encrypted at rest.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.session import Base


class Business(Base):
    """
    Business/Tenant model.
    Each business is an isolated tenant with its own data, settings, and modules.
    """
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Business type (restaurant, hotel, clinic, retail, etc.)
    business_type = Column(String(100), nullable=False, default="general")
    
    # Contact info
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), default="Beirut")
    country = Column(String(100), default="Lebanon")
    website = Column(String(500), nullable=True)
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#6366f1")  # Indigo
    secondary_color = Column(String(7), default="#8b5cf6")  # Violet
    
    # AI Settings
    ai_tone = Column(String(50), default="professional")  # professional, friendly, formal
    ai_language = Column(String(10), default="en")  # en, ar, mixed
    welcome_message = Column(Text, default="Welcome! How can we help you today?")
    
    # Configuration stored as JSON
    settings = Column(JSON, default=dict)
    
    # WhatsApp Integration (encrypted at rest via application layer)
    whatsapp_phone_number_id = Column(String(500), nullable=True)
    whatsapp_api_token = Column(String(1000), nullable=True)  # Encrypted
    whatsapp_verify_token = Column(String(100), nullable=True)
    
    # Payment Integration (encrypted at rest)
    payment_provider = Column(String(50), default="none")
    payment_api_key = Column(String(1000), nullable=True)  # Encrypted
    payment_secret_key = Column(String(1000), nullable=True)  # Encrypted
    payment_enabled = Column(Boolean, default=False)
    currency = Column(String(10), default="USD")
    
    # Soft Delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    subscription_plan = Column(String(50), default="free")  # free, starter, pro, enterprise
    subscription_expires = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="business")
    customers = relationship("Customer", back_populates="business")
    conversations = relationship("Conversation", back_populates="business")
    orders = relationship("Order", back_populates="business")
    bookings = relationship("Booking", back_populates="business")
    products = relationship("Product", back_populates="business")
    categories = relationship("Category", back_populates="business")
    services = relationship("Service", back_populates="business")
    documents = relationship("Document", back_populates="business")
    workflows = relationship("Workflow", back_populates="business")
    modules = relationship("BusinessModule", back_populates="business")
    notifications = relationship("Notification", back_populates="business")

    def __repr__(self):
        return f"<Business {self.name}>"


class BusinessModule(Base):
    """
    Tracks which modules are enabled for each business.
    Enables plug-and-play module system.
    """
    __tablename__ = "business_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    module_key = Column(String(100), nullable=False)  # restaurant, hotel, clinic, retail, delivery
    is_enabled = Column(Boolean, default=True)
    config = Column(JSON, default=dict)  # Module-specific configuration
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="modules")

    def __repr__(self):
        return f"<BusinessModule {self.module_key} for {self.business_id}>"
