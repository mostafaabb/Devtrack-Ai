"""
Business management API routes.
Handles business settings, modules, and branding.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.business import Business, BusinessModule
from app.models.module import ModuleDefinition
from app.schemas.business import BusinessUpdate, BusinessResponse, ModuleToggle

router = APIRouter(prefix="/business", tags=["Business"])


@router.get("/", response_model=BusinessResponse)
def get_business(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's business details."""
    business = db.query(Business).filter(
        Business.id == current_user["business_id"]
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.put("/", response_model=BusinessResponse)
def update_business(
    data: BusinessUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update business settings and branding."""
    business = db.query(Business).filter(
        Business.id == current_user["business_id"]
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(business, key, value)
    
    db.commit()
    db.refresh(business)
    return business


@router.get("/modules")
def get_modules(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all available modules and their status for this business."""
    # Get all module definitions
    all_modules = db.query(ModuleDefinition).all()
    
    # Get enabled modules for this business
    enabled = db.query(BusinessModule).filter(
        BusinessModule.business_id == current_user["business_id"]
    ).all()
    enabled_keys = {m.module_key: m for m in enabled}
    
    result = []
    for module in all_modules:
        bm = enabled_keys.get(module.key)
        result.append({
            "key": module.key,
            "name": module.name,
            "description": module.description,
            "icon": module.icon,
            "features": module.features,
            "is_enabled": bm.is_enabled if bm else False,
            "is_premium": module.is_premium,
            "config": bm.config if bm else {}
        })
    
    # If no module definitions exist, return defaults
    if not result:
        result = [
            {"key": "restaurant", "name": "Restaurant Module", "description": "Menu, orders, table reservations", "icon": "🍔", "features": ["Menu management", "Order system", "Table reservations", "Delivery integration"], "is_enabled": False, "is_premium": False, "config": {}},
            {"key": "hotel", "name": "Hotel Module", "description": "Room booking, guest management", "icon": "🏨", "features": ["Room booking", "Availability calendar", "Guest management", "Check-in/out"], "is_enabled": False, "is_premium": False, "config": {}},
            {"key": "retail", "name": "Retail Module", "description": "Products, inventory, orders", "icon": "🛍️", "features": ["Product catalog", "Inventory tracking", "Online orders", "Discounts"], "is_enabled": False, "is_premium": False, "config": {}},
            {"key": "clinic", "name": "Clinic Module", "description": "Appointments, schedules, patients", "icon": "🏥", "features": ["Appointments", "Doctor schedules", "Patient records", "Prescriptions"], "is_enabled": False, "is_premium": False, "config": {}},
            {"key": "delivery", "name": "Delivery Module", "description": "Order tracking, drivers", "icon": "🚚", "features": ["Order tracking", "Driver management", "Route optimization", "Delivery status"], "is_enabled": False, "is_premium": False, "config": {}},
        ]
    
    return result


@router.post("/modules/toggle")
def toggle_module(
    data: ModuleToggle,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable or disable a module for this business."""
    existing = db.query(BusinessModule).filter(
        BusinessModule.business_id == current_user["business_id"],
        BusinessModule.module_key == data.module_key
    ).first()
    
    if existing:
        existing.is_enabled = data.is_enabled
        if data.config:
            existing.config = data.config
    else:
        new_module = BusinessModule(
            business_id=current_user["business_id"],
            module_key=data.module_key,
            is_enabled=data.is_enabled,
            config=data.config or {}
        )
        db.add(new_module)
    
    db.commit()
    return {"message": f"Module '{data.module_key}' {'enabled' if data.is_enabled else 'disabled'}"}
