"""
Order and OrderItem models.
Supports orders created via chat, manually, or through integrations.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class OrderStatus(str, enum.Enum):
    """Order lifecycle status."""
    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderType(str, enum.Enum):
    """Type of order."""
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"
    DELIVERY = "delivery"
    ONLINE = "online"


class Order(Base):
    """
    Order model with status tracking and multi-type support.
    Can be created via AI chat, manually, or through API.
    """
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    
    # Order details
    order_number = Column(String(50), unique=True, nullable=False)
    order_type = Column(SQLEnum(OrderType), default=OrderType.ONLINE)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    
    # Financials
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    
    # Delivery info
    delivery_address = Column(Text, nullable=True)
    delivery_notes = Column(Text, nullable=True)
    
    # Source tracking
    source = Column(String(50), default="manual")  # manual, ai_chat, whatsapp, web
    conversation_id = Column(UUID(as_uuid=True), nullable=True)  # Link to originating conversation
    
    # Extra data
    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)
    
    # Payment tracking
    payment_id = Column(String(100), nullable=True)
    payment_url = Column(String(500), nullable=True)
    payment_status = Column(String(50), default="unpaid")
    
    # Visual AI / Attachment tracking
    image_url = Column(String(500), nullable=True) # If order was based on a photo
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.order_number} - {self.status}>"


class OrderItem(Base):
    """Individual item within an order."""
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem {self.name} x{self.quantity}>"
