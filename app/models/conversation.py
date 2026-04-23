"""
Conversation and Message models.
Handles real-time chat system with AI auto-replies and human takeover.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class ConversationStatus(str, enum.Enum):
    """Status of a conversation."""
    ACTIVE = "active"
    CLOSED = "closed"
    PENDING = "pending"        # Waiting for human response
    AI_HANDLING = "ai_handling" # AI is auto-responding


class MessageSender(str, enum.Enum):
    """Who sent the message."""
    CUSTOMER = "customer"
    AI = "ai"
    STAFF = "staff"
    SYSTEM = "system"


class Conversation(Base):
    """
    Conversation thread between a customer and a business.
    Supports AI auto-handling and human takeover.
    """
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    
    # Conversation metadata
    channel = Column(String(50), default="web")  # web, whatsapp, instagram
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.AI_HANDLING)
    subject = Column(String(255), nullable=True)
    
    # AI handling
    is_ai_enabled = Column(Boolean, default=True)
    ai_persona = Column(String(50), default="general") # general, sales, support, concierge
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Sentiment tracking
    sentiment_score = Column(Integer, default=0)  # -100 to 100
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="conversations")
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation {self.id} - {self.status}>"


class Message(Base):
    """
    Individual message within a conversation.
    Tracks sender type, content, and AI metadata.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    sender_type = Column(SQLEnum(MessageSender), nullable=False)
    sender_id = Column(UUID(as_uuid=True), nullable=True)  # User ID or Customer ID
    
    # AI metadata
    ai_intent = Column(String(50), nullable=True)        # question, order, booking, complaint
    ai_confidence = Column(Integer, nullable=True)        # 0-100
    ai_action_taken = Column(String(100), nullable=True)  # respond, create_order, escalate
    
    # Message status
    is_read = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.sender_type}: {self.content[:50]}>"
