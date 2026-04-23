"""
Coupon and discount models.
Supports percentage/fixed discounts, usage limits, date ranges, and conditions.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class DiscountType(str, enum.Enum):
    """Type of discount."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_SHIPPING = "free_shipping"
    BUY_X_GET_Y = "buy_x_get_y"


class CouponStatus(str, enum.Enum):
    """Coupon status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"  # Usage limit reached


class Coupon(Base):
    """
    Coupon/promo code model.
    Flexible discount system with usage limits and conditions.
    """
    __tablename__ = "coupons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)

    # Coupon details
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Discount configuration
    discount_type = Column(SQLEnum(DiscountType), default=DiscountType.PERCENTAGE)
    discount_value = Column(Float, nullable=False)  # Percentage (0-100) or fixed amount
    max_discount_amount = Column(Float, nullable=True)  # Cap for percentage discounts
    
    # Minimum requirements
    minimum_order_amount = Column(Float, default=0)
    minimum_quantity = Column(Integer, default=0)
    
    # Usage limits
    usage_limit = Column(Integer, nullable=True)  # Total uses allowed (null = unlimited)
    usage_limit_per_customer = Column(Integer, nullable=True)  # Per customer limit
    times_used = Column(Integer, default=0)
    
    # Validity period
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Restrictions
    applies_to = Column(String(50), default="all")  # all, products, categories, services
    applicable_ids = Column(JSON, default=list)  # List of product/category IDs
    excluded_ids = Column(JSON, default=list)  # Excluded product/category IDs
    
    # Customer restrictions
    customer_ids = Column(JSON, default=list)  # Empty = all customers
    first_order_only = Column(Boolean, default=False)
    
    # Buy X Get Y settings
    buy_quantity = Column(Integer, nullable=True)
    get_quantity = Column(Integer, nullable=True)
    get_product_ids = Column(JSON, default=list)
    
    # Status
    status = Column(SQLEnum(CouponStatus), default=CouponStatus.ACTIVE)
    is_automatic = Column(Boolean, default=False)  # Auto-apply if conditions met
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="coupons")
    usages = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Coupon {self.code} - {self.discount_type} {self.discount_value}>"

    @property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid."""
        now = datetime.utcnow()
        
        if self.status != CouponStatus.ACTIVE:
            return False
        
        if self.starts_at and now < self.starts_at:
            return False
            
        if self.expires_at and now > self.expires_at:
            return False
            
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
            
        return True

    def calculate_discount(self, subtotal: float, quantity: int = 1) -> float:
        """Calculate the discount amount for a given subtotal."""
        if not self.is_valid:
            return 0
            
        if subtotal < self.minimum_order_amount:
            return 0
            
        if quantity < self.minimum_quantity:
            return 0
        
        if self.discount_type == DiscountType.PERCENTAGE:
            discount = subtotal * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return round(discount, 2)
            
        elif self.discount_type == DiscountType.FIXED_AMOUNT:
            return min(self.discount_value, subtotal)
            
        elif self.discount_type == DiscountType.FREE_SHIPPING:
            return 0  # Handled separately in order calculation
            
        return 0


class CouponUsage(Base):
    """
    Tracks coupon usage by customers.
    """
    __tablename__ = "coupon_usages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("coupons.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    # Usage details
    discount_applied = Column(Float, nullable=False)
    order_subtotal = Column(Float, nullable=True)
    
    # Timestamps
    used_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    coupon = relationship("Coupon", back_populates="usages")
    customer = relationship("Customer", backref="coupon_usages")
    order = relationship("Order", backref="coupon_usages")

    def __repr__(self):
        return f"<CouponUsage {self.coupon_id} - {self.discount_applied}>"


class Promotion(Base):
    """
    Time-based promotions and flash sales.
    Can include multiple products with special pricing.
    """
    __tablename__ = "promotions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Promotion details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    banner_image = Column(String(500), nullable=True)
    
    # Discount
    discount_type = Column(SQLEnum(DiscountType), default=DiscountType.PERCENTAGE)
    discount_value = Column(Float, nullable=False)
    
    # Products included
    product_ids = Column(JSON, default=list)
    category_ids = Column(JSON, default=list)
    
    # Validity
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="promotions")

    def __repr__(self):
        return f"<Promotion {self.name}>"

    @property
    def is_running(self) -> bool:
        """Check if promotion is currently running."""
        now = datetime.utcnow()
        return self.is_active and self.starts_at <= now <= self.ends_at
