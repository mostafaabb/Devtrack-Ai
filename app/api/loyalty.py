"""
Loyalty Program API endpoints.
Handles points, rewards, tiers, and customer loyalty status.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.loyalty_service import loyalty_service
from app.models.loyalty import (
    LoyaltyProgram, LoyaltyTier, LoyaltyReward, CustomerLoyalty,
    LoyaltyTransaction, RewardRedemption, RewardType
)


router = APIRouter(prefix="/loyalty", tags=["Loyalty Program"])


# ═══════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════

class ProgramSettings(BaseModel):
    name: Optional[str] = None
    points_per_currency: Optional[float] = None
    currency_per_point: Optional[float] = None
    min_points_redeem: Optional[int] = None
    signup_bonus_points: Optional[int] = None
    referral_points_referrer: Optional[int] = None
    referral_points_referee: Optional[int] = None
    points_expire: Optional[bool] = None
    points_expire_days: Optional[int] = None


class TierCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#888888"
    min_points: int = 0
    points_multiplier: float = 1.0
    discount_percentage: float = 0
    free_shipping: bool = False
    tier_order: int = 1


class RewardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    points_cost: int
    reward_type: str
    reward_value: Optional[float] = None
    reward_product_id: Optional[str] = None
    min_order_amount: float = 0
    stock_quantity: Optional[int] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_featured: bool = False


class EnrollCustomer(BaseModel):
    customer_id: str
    referred_by_code: Optional[str] = None


class EarnPoints(BaseModel):
    customer_id: str
    amount: float
    order_id: Optional[str] = None
    description: Optional[str] = None


class RedeemPoints(BaseModel):
    customer_id: str
    points: int
    reward_id: Optional[str] = None
    order_id: Optional[str] = None
    description: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# Program Management
# ═══════════════════════════════════════════════════════════════════

@router.get("/program")
async def get_loyalty_program(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get loyalty program settings."""
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    return {
        "id": str(program.id),
        "name": program.name,
        "description": program.description,
        "points_per_currency": program.points_per_currency,
        "currency_per_point": program.currency_per_point,
        "min_points_redeem": program.min_points_redeem,
        "signup_bonus_points": program.signup_bonus_points,
        "referral_points_referrer": program.referral_points_referrer,
        "referral_points_referee": program.referral_points_referee,
        "points_expire": program.points_expire,
        "points_expire_days": program.points_expire_days,
        "is_active": program.is_active,
    }


@router.put("/program")
async def update_loyalty_program(
    data: ProgramSettings,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update loyalty program settings."""
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    if data.name is not None:
        program.name = data.name
    if data.points_per_currency is not None:
        program.points_per_currency = data.points_per_currency
    if data.currency_per_point is not None:
        program.currency_per_point = data.currency_per_point
    if data.min_points_redeem is not None:
        program.min_points_redeem = data.min_points_redeem
    if data.signup_bonus_points is not None:
        program.signup_bonus_points = data.signup_bonus_points
    if data.referral_points_referrer is not None:
        program.referral_points_referrer = data.referral_points_referrer
    if data.referral_points_referee is not None:
        program.referral_points_referee = data.referral_points_referee
    if data.points_expire is not None:
        program.points_expire = data.points_expire
    if data.points_expire_days is not None:
        program.points_expire_days = data.points_expire_days
    
    program.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Tiers
# ═══════════════════════════════════════════════════════════════════

@router.get("/tiers")
async def list_tiers(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all loyalty tiers."""
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    tiers = db.query(LoyaltyTier).filter(
        LoyaltyTier.program_id == program.id
    ).order_by(LoyaltyTier.tier_order).all()
    
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "color": t.color,
            "min_points": t.min_points,
            "points_multiplier": t.points_multiplier,
            "discount_percentage": t.discount_percentage,
            "free_shipping": t.free_shipping,
            "tier_order": t.tier_order,
        }
        for t in tiers
    ]


@router.post("/tiers")
async def create_tier(
    data: TierCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new loyalty tier."""
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    tier = LoyaltyTier(
        program_id=program.id,
        name=data.name,
        description=data.description,
        color=data.color,
        min_points=data.min_points,
        points_multiplier=data.points_multiplier,
        discount_percentage=data.discount_percentage,
        free_shipping=data.free_shipping,
        tier_order=data.tier_order,
    )
    db.add(tier)
    db.commit()
    
    return {"success": True, "tier_id": str(tier.id)}


@router.put("/tiers/{tier_id}")
async def update_tier(
    tier_id: UUID,
    data: TierCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a loyalty tier."""
    tier = db.query(LoyaltyTier).filter(LoyaltyTier.id == tier_id).first()
    
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")
    
    tier.name = data.name
    tier.description = data.description
    tier.color = data.color
    tier.min_points = data.min_points
    tier.points_multiplier = data.points_multiplier
    tier.discount_percentage = data.discount_percentage
    tier.free_shipping = data.free_shipping
    tier.tier_order = data.tier_order
    tier.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Rewards
# ═══════════════════════════════════════════════════════════════════

@router.get("/rewards")
async def list_rewards(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all loyalty rewards."""
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    query = db.query(LoyaltyReward).filter(
        LoyaltyReward.program_id == program.id
    )
    
    if active_only:
        query = query.filter(LoyaltyReward.is_active == True)
    
    rewards = query.order_by(LoyaltyReward.points_cost).all()
    
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "image_url": r.image_url,
            "points_cost": r.points_cost,
            "reward_type": r.reward_type.value,
            "reward_value": r.reward_value,
            "stock_quantity": r.stock_quantity,
            "times_redeemed": r.times_redeemed,
            "is_active": r.is_active,
            "is_featured": r.is_featured,
            "is_available": r.is_available,
        }
        for r in rewards
    ]


@router.post("/rewards")
async def create_reward(
    data: RewardCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new reward."""
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    try:
        reward_type = RewardType(data.reward_type)
    except ValueError:
        reward_type = RewardType.DISCOUNT_PERCENTAGE
    
    reward = LoyaltyReward(
        program_id=program.id,
        name=data.name,
        description=data.description,
        image_url=data.image_url,
        points_cost=data.points_cost,
        reward_type=reward_type,
        reward_value=data.reward_value,
        reward_product_id=data.reward_product_id,
        min_order_amount=data.min_order_amount,
        stock_quantity=data.stock_quantity,
        starts_at=data.starts_at,
        expires_at=data.expires_at,
        is_featured=data.is_featured,
    )
    db.add(reward)
    db.commit()
    
    return {"success": True, "reward_id": str(reward.id)}


# ═══════════════════════════════════════════════════════════════════
# Customer Loyalty
# ═══════════════════════════════════════════════════════════════════

@router.post("/enroll")
async def enroll_customer(
    data: EnrollCustomer,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enroll a customer in the loyalty program."""
    result = await loyalty_service.enroll_customer(
        db=db,
        business_id=str(current_user["business_id"]),
        customer_id=data.customer_id,
        referred_by_code=data.referred_by_code,
    )
    
    return result


@router.post("/earn")
async def earn_points(
    data: EarnPoints,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Award points to a customer for a purchase."""
    result = await loyalty_service.earn_points(
        db=db,
        business_id=str(current_user["business_id"]),
        customer_id=data.customer_id,
        amount=data.amount,
        order_id=data.order_id,
        description=data.description,
    )
    
    return result


@router.post("/redeem")
async def redeem_points(
    data: RedeemPoints,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Redeem points for rewards or discount."""
    result = await loyalty_service.redeem_points(
        db=db,
        customer_id=data.customer_id,
        points=data.points,
        reward_id=data.reward_id,
        order_id=data.order_id,
        description=data.description,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/customer/{customer_id}")
def get_customer_loyalty(
    customer_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get customer's loyalty status."""
    return loyalty_service.get_customer_loyalty_status(db, str(customer_id))


@router.get("/customer/{customer_id}/transactions")
def get_customer_transactions(
    customer_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get customer's loyalty transaction history."""
    customer_loyalty = db.query(CustomerLoyalty).filter(
        CustomerLoyalty.customer_id == customer_id
    ).first()
    
    if not customer_loyalty:
        return []
    
    transactions = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.customer_loyalty_id == customer_loyalty.id
    ).order_by(
        LoyaltyTransaction.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return [
        {
            "id": str(t.id),
            "transaction_type": t.transaction_type.value,
            "points": t.points,
            "balance_after": t.balance_after,
            "description": t.description,
            "reference_type": t.reference_type,
            "created_at": t.created_at.isoformat(),
        }
        for t in transactions
    ]


@router.get("/members")
async def list_loyalty_members(
    tier_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all loyalty program members."""
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    query = db.query(CustomerLoyalty).filter(
        CustomerLoyalty.program_id == program.id
    )
    
    if tier_id:
        query = query.filter(CustomerLoyalty.tier_id == tier_id)
    
    members = query.order_by(
        CustomerLoyalty.points_earned_total.desc()
    ).offset(offset).limit(limit).all()
    
    return [
        {
            "id": str(m.id),
            "customer_id": str(m.customer_id),
            "points_balance": m.points_balance,
            "points_earned_total": m.points_earned_total,
            "tier_id": str(m.tier_id) if m.tier_id else None,
            "tier_name": m.tier.name if m.tier else None,
            "total_spent": m.total_spent,
            "total_orders": m.total_orders,
            "referral_code": m.referral_code,
            "referral_count": m.referral_count,
            "joined_at": m.joined_at.isoformat(),
            "last_activity_at": m.last_activity_at.isoformat() if m.last_activity_at else None,
        }
        for m in members
    ]


@router.get("/stats")
async def get_loyalty_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get loyalty program statistics."""
    from sqlalchemy import func
    
    program = await loyalty_service.get_or_create_program(
        db, str(current_user["business_id"])
    )
    
    total_members = db.query(CustomerLoyalty).filter(
        CustomerLoyalty.program_id == program.id
    ).count()
    
    stats = db.query(
        func.sum(CustomerLoyalty.points_earned_total).label("total_earned"),
        func.sum(CustomerLoyalty.points_redeemed_total).label("total_redeemed"),
        func.sum(CustomerLoyalty.points_balance).label("outstanding"),
    ).filter(
        CustomerLoyalty.program_id == program.id
    ).first()
    
    return {
        "total_members": total_members,
        "total_points_earned": stats.total_earned or 0,
        "total_points_redeemed": stats.total_redeemed or 0,
        "outstanding_points": stats.outstanding or 0,
        "outstanding_value": (stats.outstanding or 0) * program.currency_per_point,
    }
