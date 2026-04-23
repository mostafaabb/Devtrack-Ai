"""
Pydantic schemas for conversations, messages, customers, orders, bookings, products, etc.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ─── Customer Schemas ───────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: str = "web"
    tags: Optional[List[str]] = []

class CustomerResponse(BaseModel):
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: str
    tags: list
    created_at: datetime
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Conversation Schemas ───────────────────────────────────────────

class ConversationCreate(BaseModel):
    customer_id: UUID
    channel: str = "web"
    subject: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    sender_type: str = "customer"  # customer, staff

class MessageResponse(BaseModel):
    id: UUID
    content: str
    sender_type: str
    ai_intent: Optional[str] = None
    ai_confidence: Optional[int] = None
    ai_action_taken: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: UUID
    customer_id: UUID
    channel: str
    status: str
    subject: Optional[str] = None
    is_ai_enabled: bool
    ai_persona: Optional[str] = "general"
    sentiment_score: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    messages: Optional[List[MessageResponse]] = []
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True


# ─── Order Schemas ──────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: Optional[UUID] = None
    name: str
    quantity: int = 1
    unit_price: float = 0.0
    notes: Optional[str] = None

class OrderCreate(BaseModel):
    customer_id: Optional[UUID] = None
    order_type: str = "online"
    items: List[OrderItemCreate] = []
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    notes: Optional[str] = None
    source: str = "manual"

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    order_type: str
    status: str
    subtotal: float
    tax: float
    discount: float
    delivery_fee: float
    total: float
    currency: str
    delivery_address: Optional[str] = None
    source: str
    notes: Optional[str] = None
    created_at: datetime
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True


# ─── Booking Schemas ────────────────────────────────────────────────

class BookingCreate(BaseModel):
    customer_id: Optional[UUID] = None
    booking_type: str = "service"
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    party_size: int = 1
    resource_name: Optional[str] = None
    service_name: Optional[str] = None
    notes: Optional[str] = None
    source: str = "manual"

class BookingUpdate(BaseModel):
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None

class BookingResponse(BaseModel):
    id: UUID
    booking_number: str
    booking_type: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    party_size: int
    resource_name: Optional[str] = None
    service_name: Optional[str] = None
    price: float
    source: str
    notes: Optional[str] = None
    created_at: datetime
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True


# ─── Product Schemas ────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    price: float = 0.0
    sale_price: Optional[float] = None
    sku: Optional[str] = None
    stock_quantity: Optional[int] = None
    track_inventory: bool = False
    image_url: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    price: float
    sale_price: Optional[float] = None
    sku: Optional[str] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None
    is_active: bool
    is_featured: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None

class CategoryResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Service Schemas ────────────────────────────────────────────────

class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int = 60
    price: float = 0.0

class ServiceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Document Schemas ───────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: UUID
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Workflow Schemas ───────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_conditions: Optional[Dict[str, Any]] = {}
    action_type: str
    action_config: Optional[Dict[str, Any]] = {}

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    action_config: Optional[Dict[str, Any]] = None

class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    status: str
    trigger_type: str
    trigger_conditions: dict
    action_type: str
    action_config: dict
    execution_count: dict
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Analytics Schemas ──────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_customers: int = 0
    total_conversations: int = 0
    total_orders: int = 0
    total_bookings: int = 0
    total_revenue: float = 0.0
    active_conversations: int = 0
    pending_orders: int = 0
    pending_bookings: int = 0

class ChatMessage(BaseModel):
    """Schema for incoming chat messages (web widget)."""
    message: str
    customer_id: Optional[str] = None
    business_slug: str
    channel: str = "web"
