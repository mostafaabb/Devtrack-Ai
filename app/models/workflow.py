"""
Workflow model for the automation engine.
Supports IF/THEN logic for business process automation.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class WorkflowStatus(str, enum.Enum):
    """Workflow status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class Workflow(Base):
    """
    Automation workflow with IF/THEN trigger logic.
    
    Examples:
    - IF customer sends message -> AI replies
    - IF order placed -> notify admin
    - IF booking requested -> confirm or suggest time
    """
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Workflow info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.ACTIVE)
    
    # Trigger configuration (IF)
    trigger_type = Column(String(100), nullable=False)  # message_received, order_placed, booking_requested, etc.
    trigger_conditions = Column(JSON, default=dict)      # Conditions to match
    
    # Action configuration (THEN)
    action_type = Column(String(100), nullable=False)   # ai_reply, notify_admin, create_booking, send_email, etc.
    action_config = Column(JSON, default=dict)           # Action parameters
    
    # Execution stats
    execution_count = Column(JSON, default={"total": 0, "success": 0, "failed": 0})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="workflows")
    logs = relationship("WorkflowLog", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workflow {self.name}>"


class WorkflowLog(Base):
    """Log entry for workflow executions."""
    __tablename__ = "workflow_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    
    status = Column(String(50), nullable=False)  # success, failed, skipped
    trigger_data = Column(JSON, default=dict)     # Data that triggered the workflow
    action_result = Column(JSON, default=dict)    # Result of the action
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="logs")

    def __repr__(self):
        return f"<WorkflowLog {self.workflow_id} - {self.status}>"
