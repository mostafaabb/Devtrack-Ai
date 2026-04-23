"""
Module definition model.
Defines available industry modules that businesses can enable.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.db.session import Base


class ModuleDefinition(Base):
    """
    Defines an available module in the system.
    Modules are industry-specific feature packs (restaurant, hotel, clinic, etc.).
    """
    __tablename__ = "module_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    key = Column(String(100), unique=True, nullable=False)  # restaurant, hotel, clinic, retail, delivery
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon identifier
    
    # Module features
    features = Column(JSON, default=list)  # List of feature descriptions
    
    # Status
    is_available = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    
    # Default configuration
    default_config = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ModuleDefinition {self.key}>"
