"""
Marketing campaign models.
Supports email campaigns, SMS campaigns, templates, and tracking.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class CampaignType(str, enum.Enum):
    """Type of marketing campaign."""
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    MULTI_CHANNEL = "multi_channel"


class CampaignStatus(str, enum.Enum):
    """Campaign status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RecipientStatus(str, enum.Enum):
    """Individual recipient status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"


class TriggerType(str, enum.Enum):
    """Automation trigger types."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    ORDER_PLACED = "order_placed"
    ORDER_COMPLETED = "order_completed"
    BOOKING_CONFIRMED = "booking_confirmed"
    CUSTOMER_BIRTHDAY = "customer_birthday"
    CUSTOMER_SIGNUP = "customer_signup"
    CART_ABANDONED = "cart_abandoned"
    INACTIVE_CUSTOMER = "inactive_customer"
    LOYALTY_MILESTONE = "loyalty_milestone"


class Campaign(Base):
    """
    Marketing campaign model.
    Supports email, SMS, WhatsApp, and multi-channel campaigns.
    """
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Campaign details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignType), default=CampaignType.EMAIL)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT)
    
    # Content
    subject = Column(String(500), nullable=True)  # Email subject
    content = Column(Text, nullable=True)  # Main content/body
    html_content = Column(Text, nullable=True)  # HTML version for emails
    template_id = Column(UUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=True)
    
    # Sender info
    from_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)
    reply_to = Column(String(255), nullable=True)
    
    # Targeting
    segment_rules = Column(JSON, default=dict)  # Customer segment rules
    customer_tags = Column(JSON, default=list)  # Target specific tags
    exclude_tags = Column(JSON, default=list)
    
    # Scheduling
    trigger_type = Column(SQLEnum(TriggerType), default=TriggerType.MANUAL)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    
    # Statistics
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    unsubscribed_count = Column(Integer, default=0)
    
    # Revenue attribution
    revenue_attributed = Column(Float, default=0)
    orders_attributed = Column(Integer, default=0)
    
    # Settings
    track_opens = Column(Boolean, default=True)
    track_clicks = Column(Boolean, default=True)
    
    # A/B Testing
    is_ab_test = Column(Boolean, default=False)
    ab_variant = Column(String(10), nullable=True)  # A, B, C
    ab_parent_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    
    # Created by
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="campaigns")
    template = relationship("EmailTemplate", backref="campaigns")
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campaign {self.name} - {self.status}>"

    @property
    def open_rate(self) -> float:
        if self.delivered_count == 0:
            return 0
        return round((self.opened_count / self.delivered_count) * 100, 2)

    @property
    def click_rate(self) -> float:
        if self.delivered_count == 0:
            return 0
        return round((self.clicked_count / self.delivered_count) * 100, 2)


class EmailTemplate(Base):
    """
    Reusable email/SMS templates.
    """
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Template details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(SQLEnum(CampaignType), default=CampaignType.EMAIL)
    
    # Content
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)  # Plain text
    html_content = Column(Text, nullable=True)  # HTML
    
    # Variables available: {{customer_name}}, {{business_name}}, {{order_number}}, etc.
    variables = Column(JSON, default=list)
    
    # Category
    category = Column(String(100), nullable=True)  # marketing, transactional, notification
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="email_templates")

    def __repr__(self):
        return f"<EmailTemplate {self.name}>"

    def render(self, variables: dict) -> tuple:
        """Render template with variables."""
        subject = self.subject or ""
        content = self.content or ""
        html = self.html_content or ""
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))
            html = html.replace(placeholder, str(value))
        
        return subject, content, html


class CampaignRecipient(Base):
    """
    Individual campaign recipients with status tracking.
    """
    __tablename__ = "campaign_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    
    # Contact info
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    name = Column(String(255), nullable=True)
    
    # Status
    status = Column(SQLEnum(RecipientStatus), default=RecipientStatus.PENDING)
    
    # Tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    
    # Links clicked
    clicked_links = Column(JSON, default=list)
    
    # Error tracking
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="recipients")
    customer = relationship("Customer", backref="campaign_recipients")

    def __repr__(self):
        return f"<CampaignRecipient {self.email} - {self.status}>"


class CampaignLink(Base):
    """
    Trackable links in campaigns.
    """
    __tablename__ = "campaign_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    
    # Link details
    original_url = Column(String(2000), nullable=False)
    tracking_code = Column(String(50), unique=True, nullable=False)
    label = Column(String(255), nullable=True)
    
    # Statistics
    click_count = Column(Integer, default=0)
    unique_clicks = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", backref="links")

    def __repr__(self):
        return f"<CampaignLink {self.tracking_code}>"


class Unsubscribe(Base):
    """
    Unsubscribed contacts.
    """
    __tablename__ = "unsubscribes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    
    # Contact
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Unsubscribe details
    channel = Column(SQLEnum(CampaignType), nullable=True)  # All if null
    reason = Column(Text, nullable=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    
    # Timestamps
    unsubscribed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="unsubscribes")
    customer = relationship("Customer", backref="unsubscribes")
    campaign = relationship("Campaign", backref="unsubscribes")

    def __repr__(self):
        return f"<Unsubscribe {self.email or self.phone}>"
