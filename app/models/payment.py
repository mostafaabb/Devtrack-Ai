"""
Payment models for Stripe integration.
Supports payments, refunds, payment methods, and subscriptions.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class PaymentStatus(str, enum.Enum):
    """Payment status lifecycle."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, enum.Enum):
    """Supported payment methods."""
    CARD = "card"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    WHATSAPP_PAY = "whatsapp_pay"
    STRIPE = "stripe"
    PAYPAL = "paypal"


class RefundStatus(str, enum.Enum):
    """Refund status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Payment(Base):
    """
    Payment model - tracks all payments for orders/bookings.
    Integrates with Stripe for card payments.
    """
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)

    # Payment details
    payment_number = Column(String(50), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    method = Column(SQLEnum(PaymentMethod), default=PaymentMethod.CARD)

    # Stripe integration
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)
    stripe_charge_id = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_payment_method_id = Column(String(255), nullable=True)
    
    # Payment link (for WhatsApp/SMS checkout)
    checkout_url = Column(String(500), nullable=True)
    checkout_expires_at = Column(DateTime, nullable=True)

    # Card details (masked)
    card_brand = Column(String(50), nullable=True)  # visa, mastercard, amex
    card_last4 = Column(String(4), nullable=True)
    card_exp_month = Column(Integer, nullable=True)
    card_exp_year = Column(Integer, nullable=True)

    # Failure tracking
    failure_code = Column(String(100), nullable=True)
    failure_message = Column(Text, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    extra_metadata = Column(JSON, default=dict)
    receipt_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", backref="payments")
    customer = relationship("Customer", backref="payments")
    order = relationship("Order", backref="payments")
    booking = relationship("Booking", backref="payments")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Payment {self.payment_number} - {self.amount} {self.currency} - {self.status}>"

    @property
    def is_paid(self) -> bool:
        return self.status == PaymentStatus.SUCCEEDED

    @property
    def refunded_amount(self) -> float:
        return sum(r.amount for r in self.refunds if r.status == RefundStatus.SUCCEEDED)

    @property
    def net_amount(self) -> float:
        return self.amount - self.refunded_amount


class Refund(Base):
    """
    Refund model - tracks refunds for payments.
    """
    __tablename__ = "refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    
    # Refund details
    refund_number = Column(String(50), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(SQLEnum(RefundStatus), default=RefundStatus.PENDING)

    # Stripe integration
    stripe_refund_id = Column(String(255), nullable=True)

    # Metadata
    extra_metadata = Column(JSON, default=dict)
    
    # Who initiated the refund
    initiated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    payment = relationship("Payment", back_populates="refunds")

    def __repr__(self):
        return f"<Refund {self.refund_number} - {self.amount} - {self.status}>"


class CustomerPaymentMethod(Base):
    """
    Stored payment methods for customers.
    Enables quick checkout and recurring payments.
    """
    __tablename__ = "customer_payment_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    # Stripe
    stripe_payment_method_id = Column(String(255), nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)

    # Card info (masked)
    card_brand = Column(String(50), nullable=True)
    card_last4 = Column(String(4), nullable=True)
    card_exp_month = Column(Integer, nullable=True)
    card_exp_year = Column(Integer, nullable=True)

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="customer_payment_methods")
    customer = relationship("Customer", backref="payment_methods")

    def __repr__(self):
        return f"<PaymentMethod {self.card_brand} ****{self.card_last4}>"
