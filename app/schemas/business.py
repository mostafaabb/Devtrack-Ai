"""
Pydantic schemas for business management.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class BusinessCreate(BaseModel):
    """Schema for creating a business."""
    name: str
    business_type: str = "general"
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: str = "Beirut"


class BusinessUpdate(BaseModel):
    """Schema for updating business settings."""
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    ai_tone: Optional[str] = None
    ai_language: Optional[str] = None
    welcome_message: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    
    # WhatsApp Integration
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_api_token: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    
    # Payment Integration
    payment_provider: Optional[str] = None
    payment_api_key: Optional[str] = None
    payment_enabled: Optional[bool] = None


class BusinessResponse(BaseModel):
    """Schema for business response."""
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    business_type: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: str
    country: str
    logo_url: Optional[str] = None
    primary_color: str
    secondary_color: str
    ai_tone: str
    ai_language: str
    welcome_message: str
    subscription_plan: str
    is_active: bool
    
    # WhatsApp Integration
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_api_token: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    
    # Payment Integration
    payment_provider: str
    payment_api_key: Optional[str] = None
    payment_enabled: bool
    
    created_at: datetime

    class Config:
        from_attributes = True


class ModuleToggle(BaseModel):
    """Schema for enabling/disabling a module."""
    module_key: str
    is_enabled: bool
    config: Optional[Dict[str, Any]] = None
