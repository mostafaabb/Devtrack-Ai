"""
Coupon and Promotion API endpoints.
Handles coupon validation, creation, and management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.coupon_service import coupon_service
from app.models.coupon import Coupon, CouponUsage, Promotion, DiscountType, CouponStatus


router = APIRouter(prefix="/coupons", tags=["Coupons & Promotions"])


# ═══════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════

class CouponValidate(BaseModel):
    code: str
    subtotal: float = 0
    quantity: int = 1
    product_ids: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None
    customer_id: Optional[str] = None


class CouponCreate(BaseModel):
    code: str
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: str = "percentage"
    discount_value: float
    max_discount_amount: Optional[float] = None
    minimum_order_amount: float = 0
    minimum_quantity: int = 0
    usage_limit: Optional[int] = None
    usage_limit_per_customer: Optional[int] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    applies_to: str = "all"
    applicable_ids: Optional[List[str]] = None
    first_order_only: bool = False
    is_automatic: bool = False


class CouponUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_value: Optional[float] = None
    max_discount_amount: Optional[float] = None
    minimum_order_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    status: Optional[str] = None


class PromotionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    discount_type: str = "percentage"
    discount_value: float
    product_ids: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None
    starts_at: datetime
    ends_at: datetime
    is_featured: bool = False


# ═══════════════════════════════════════════════════════════════════
# Coupon Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/validate")
async def validate_coupon(
    data: CouponValidate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validate a coupon code and calculate discount.
    Does not apply the coupon - use /apply for that.
    """
    result = await coupon_service.validate_coupon(
        db=db,
        business_id=str(current_user["business_id"]),
        code=data.code,
        customer_id=data.customer_id,
        subtotal=data.subtotal,
        quantity=data.quantity,
        product_ids=data.product_ids,
        category_ids=data.category_ids,
    )
    
    return result


@router.post("/apply")
async def apply_coupon(
    code: str,
    order_id: str,
    subtotal: float,
    customer_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a coupon to an order."""
    result = await coupon_service.apply_coupon(
        db=db,
        business_id=str(current_user["business_id"]),
        code=code,
        order_id=order_id,
        customer_id=customer_id,
        subtotal=subtotal,
    )
    
    if not result.get("valid", True) and not result.get("success", True):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/automatic")
def get_automatic_coupons(
    subtotal: float,
    customer_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get automatically applicable coupons for cart."""
    return coupon_service.get_automatic_coupons(
        db=db,
        business_id=str(current_user["business_id"]),
        subtotal=subtotal,
        customer_id=customer_id,
    )


@router.get("/")
def list_coupons(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all coupons for the business."""
    query = db.query(Coupon).filter(
        Coupon.business_id == current_user["business_id"]
    )
    
    if status:
        try:
            query = query.filter(Coupon.status == CouponStatus(status))
        except ValueError:
            pass
    
    coupons = query.order_by(Coupon.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "description": c.description,
            "discount_type": c.discount_type.value,
            "discount_value": c.discount_value,
            "max_discount_amount": c.max_discount_amount,
            "minimum_order_amount": c.minimum_order_amount,
            "usage_limit": c.usage_limit,
            "times_used": c.times_used,
            "starts_at": c.starts_at.isoformat() if c.starts_at else None,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "status": c.status.value,
            "is_automatic": c.is_automatic,
            "is_valid": c.is_valid,
        }
        for c in coupons
    ]


@router.post("/")
async def create_coupon(
    data: CouponCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new coupon."""
    try:
        discount_type = DiscountType(data.discount_type)
    except ValueError:
        discount_type = DiscountType.PERCENTAGE
    
    result = await coupon_service.create_coupon(
        db=db,
        business_id=str(current_user["business_id"]),
        code=data.code,
        discount_type=discount_type,
        discount_value=data.discount_value,
        name=data.name,
        description=data.description,
        minimum_order_amount=data.minimum_order_amount,
        minimum_quantity=data.minimum_quantity,
        max_discount_amount=data.max_discount_amount,
        usage_limit=data.usage_limit,
        usage_limit_per_customer=data.usage_limit_per_customer,
        starts_at=data.starts_at,
        expires_at=data.expires_at,
        applies_to=data.applies_to,
        applicable_ids=data.applicable_ids,
        first_order_only=data.first_order_only,
        is_automatic=data.is_automatic,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{coupon_id}")
def get_coupon(
    coupon_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get coupon details."""
    coupon = db.query(Coupon).filter(
        Coupon.id == coupon_id,
        Coupon.business_id == current_user["business_id"],
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    return {
        "id": str(coupon.id),
        "code": coupon.code,
        "name": coupon.name,
        "description": coupon.description,
        "discount_type": coupon.discount_type.value,
        "discount_value": coupon.discount_value,
        "max_discount_amount": coupon.max_discount_amount,
        "minimum_order_amount": coupon.minimum_order_amount,
        "minimum_quantity": coupon.minimum_quantity,
        "usage_limit": coupon.usage_limit,
        "usage_limit_per_customer": coupon.usage_limit_per_customer,
        "times_used": coupon.times_used,
        "starts_at": coupon.starts_at.isoformat() if coupon.starts_at else None,
        "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
        "applies_to": coupon.applies_to,
        "applicable_ids": coupon.applicable_ids,
        "first_order_only": coupon.first_order_only,
        "is_automatic": coupon.is_automatic,
        "status": coupon.status.value,
        "is_valid": coupon.is_valid,
        "created_at": coupon.created_at.isoformat(),
    }


@router.put("/{coupon_id}")
def update_coupon(
    coupon_id: UUID,
    data: CouponUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a coupon."""
    coupon = db.query(Coupon).filter(
        Coupon.id == coupon_id,
        Coupon.business_id == current_user["business_id"],
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    if data.name is not None:
        coupon.name = data.name
    if data.description is not None:
        coupon.description = data.description
    if data.discount_value is not None:
        coupon.discount_value = data.discount_value
    if data.max_discount_amount is not None:
        coupon.max_discount_amount = data.max_discount_amount
    if data.minimum_order_amount is not None:
        coupon.minimum_order_amount = data.minimum_order_amount
    if data.usage_limit is not None:
        coupon.usage_limit = data.usage_limit
    if data.expires_at is not None:
        coupon.expires_at = data.expires_at
    if data.status is not None:
        try:
            coupon.status = CouponStatus(data.status)
        except ValueError:
            pass
    
    coupon.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


@router.delete("/{coupon_id}")
def delete_coupon(
    coupon_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a coupon."""
    coupon = db.query(Coupon).filter(
        Coupon.id == coupon_id,
        Coupon.business_id == current_user["business_id"],
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    db.delete(coupon)
    db.commit()
    
    return {"success": True}


@router.get("/stats/summary")
def get_coupon_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get coupon usage statistics."""
    return coupon_service.get_coupon_stats(
        db, str(current_user["business_id"])
    )


# ═══════════════════════════════════════════════════════════════════
# Promotions Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/promotions")
def list_promotions(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all promotions."""
    query = db.query(Promotion).filter(
        Promotion.business_id == current_user["business_id"]
    )
    
    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            Promotion.is_active == True,
            Promotion.starts_at <= now,
            Promotion.ends_at >= now,
        )
    
    promotions = query.order_by(Promotion.starts_at.desc()).all()
    
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "discount_type": p.discount_type.value,
            "discount_value": p.discount_value,
            "product_ids": p.product_ids,
            "category_ids": p.category_ids,
            "starts_at": p.starts_at.isoformat(),
            "ends_at": p.ends_at.isoformat(),
            "is_active": p.is_active,
            "is_featured": p.is_featured,
            "is_running": p.is_running,
        }
        for p in promotions
    ]


@router.post("/promotions")
def create_promotion(
    data: PromotionCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new promotion."""
    try:
        discount_type = DiscountType(data.discount_type)
    except ValueError:
        discount_type = DiscountType.PERCENTAGE
    
    promotion = Promotion(
        business_id=current_user["business_id"],
        name=data.name,
        description=data.description,
        discount_type=discount_type,
        discount_value=data.discount_value,
        product_ids=data.product_ids or [],
        category_ids=data.category_ids or [],
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        is_featured=data.is_featured,
    )
    db.add(promotion)
    db.commit()
    
    return {"success": True, "promotion_id": str(promotion.id)}
