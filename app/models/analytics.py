"""
Analytics model for tracking business events and metrics.
Powers the analytics dashboard and AI insights.
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.db.session import Base


class AnalyticsEvent(Base):
    """
    Analytics event for tracking business metrics.
    Events are aggregated to generate insights and reports.
    """
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Event info
    event_type = Column(String(100), nullable=False)  # message, order, booking, pageview, etc.
    event_action = Column(String(100), nullable=True)  # created, completed, cancelled, etc.
    
    # Reference to related entity
    entity_type = Column(String(50), nullable=True)   # conversation, order, booking, customer
    entity_id = Column(String(255), nullable=True)
    
    # Numeric value (revenue, count, etc.)
    value = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Channel tracking
    channel = Column(String(50), nullable=True)  # web, whatsapp, api
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AnalyticsEvent {self.event_type}:{self.event_action}>"
