"""
Product and Category models.
Supports menu items, retail products, hotel rooms, clinic services, etc.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.session import Base


class Category(Base):
    """Product/service category for organizing items."""
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon identifier
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="categories")
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class Product(Base):
    """
    Product model - represents items that can be ordered or booked.
    Works across industries: menu items, retail products, hotel rooms, etc.
    """
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    # Product info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sku = Column(String(100), nullable=True)
    
    # Pricing
    price = Column(Float, default=0.0)
    sale_price = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    
    # Inventory
    stock_quantity = Column(Integer, nullable=True)
    track_inventory = Column(Boolean, default=False)
    
    # Media
    image_url = Column(String(500), nullable=True)
    images = Column(JSON, default=list)  # Multiple image URLs
    
    # Attributes
    attributes = Column(JSON, default=dict)  # size, color, etc.
    tags = Column(JSON, default=list)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="products")
    category = relationship("Category", back_populates="products")

    def __repr__(self):
        return f"<Product {self.name} - ${self.price}>"
