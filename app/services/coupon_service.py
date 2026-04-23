"""
Coupon Service - Discount and promotion management.
Handles coupon validation, application, and usage tracking.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.coupon import (
    Coupon, CouponUsage, Promotion,
    DiscountType, CouponStatus
)
from app.models.customer import Customer
from app.models.order import Order

logger = logging.getLogger("devtrack.coupons")


class CouponService:
    """
    Coupon and promotion management service.
    Handles validation, application, and tracking.
    """

    async def validate_coupon(
        self,
        db: Session,
        business_id: str,
        code: str,
        customer_id: str = None,
        subtotal: float = 0,
        quantity: int = 1,
        product_ids: List[str] = None,
        category_ids: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate a coupon code and calculate discount.
        """
        coupon = db.query(Coupon).filter(
            Coupon.business_id == business_id,
            Coupon.code == code.upper(),
        ).first()

        if not coupon:
            return {"valid": False, "error": "Invalid coupon code"}

        # Check basic validity
        if not coupon.is_valid:
            if coupon.status == CouponStatus.EXPIRED:
                return {"valid": False, "error": "Coupon has expired"}
            if coupon.status == CouponStatus.EXHAUSTED:
                return {"valid": False, "error": "Coupon usage limit reached"}
            return {"valid": False, "error": "Coupon is not active"}

        # Check date validity
        now = datetime.utcnow()
        if coupon.starts_at and now < coupon.starts_at:
            return {"valid": False, "error": "Coupon is not yet active"}
        if coupon.expires_at and now > coupon.expires_at:
            return {"valid": False, "error": "Coupon has expired"}

        # Check minimum requirements
        if subtotal < coupon.minimum_order_amount:
            return {
                "valid": False, 
                "error": f"Minimum order amount is ${coupon.minimum_order_amount:.2f}"
            }
        if quantity < coupon.minimum_quantity:
            return {
                "valid": False,
                "error": f"Minimum quantity is {coupon.minimum_quantity} items"
            }

        # Check per-customer limit
        if customer_id and coupon.usage_limit_per_customer:
            customer_uses = db.query(CouponUsage).filter(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.customer_id == customer_id,
            ).count()
            
            if customer_uses >= coupon.usage_limit_per_customer:
                return {"valid": False, "error": "You have already used this coupon"}

        # Check first order only
        if coupon.first_order_only and customer_id:
            existing_orders = db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.business_id == business_id,
            ).count()
            
            if existing_orders > 0:
                return {"valid": False, "error": "This coupon is only for first orders"}

        # Check customer restrictions
        if coupon.customer_ids and customer_id:
            if str(customer_id) not in coupon.customer_ids:
                return {"valid": False, "error": "This coupon is not available for your account"}

        # Check product/category restrictions
        if coupon.applies_to == "products" and product_ids:
            if not any(pid in coupon.applicable_ids for pid in product_ids):
                return {"valid": False, "error": "Coupon not applicable to these products"}
        
        if coupon.applies_to == "categories" and category_ids:
            if not any(cid in coupon.applicable_ids for cid in category_ids):
                return {"valid": False, "error": "Coupon not applicable to these categories"}

        # Calculate discount
        discount = coupon.calculate_discount(subtotal, quantity)

        return {
            "valid": True,
            "coupon_id": str(coupon.id),
            "code": coupon.code,
            "discount_type": coupon.discount_type.value,
            "discount_value": coupon.discount_value,
            "discount_amount": discount,
            "free_shipping": coupon.discount_type == DiscountType.FREE_SHIPPING,
            "description": coupon.description,
        }

    async def apply_coupon(
        self,
        db: Session,
        business_id: str,
        code: str,
        order_id: str,
        customer_id: str = None,
        subtotal: float = 0,
    ) -> Dict[str, Any]:
        """
        Apply a coupon to an order.
        """
        # Validate first
        validation = await self.validate_coupon(
            db, business_id, code, customer_id, subtotal
        )

        if not validation.get("valid"):
            return validation

        coupon = db.query(Coupon).filter(
            Coupon.id == validation["coupon_id"]
        ).first()

        # Record usage
        usage = CouponUsage(
            coupon_id=coupon.id,
            customer_id=customer_id,
            order_id=order_id,
            discount_applied=validation["discount_amount"],
            order_subtotal=subtotal,
        )
        db.add(usage)

        # Increment usage count
        coupon.times_used += 1

        # Check if exhausted
        if coupon.usage_limit and coupon.times_used >= coupon.usage_limit:
            coupon.status = CouponStatus.EXHAUSTED

        db.commit()

        return {
            "success": True,
            "discount_applied": validation["discount_amount"],
            "free_shipping": validation.get("free_shipping", False),
        }

    async def create_coupon(
        self,
        db: Session,
        business_id: str,
        code: str,
        discount_type: DiscountType,
        discount_value: float,
        name: str = None,
        description: str = None,
        minimum_order_amount: float = 0,
        minimum_quantity: int = 0,
        max_discount_amount: float = None,
        usage_limit: int = None,
        usage_limit_per_customer: int = None,
        starts_at: datetime = None,
        expires_at: datetime = None,
        applies_to: str = "all",
        applicable_ids: List[str] = None,
        first_order_only: bool = False,
        is_automatic: bool = False,
    ) -> Dict[str, Any]:
        """Create a new coupon."""
        # Check for duplicate code
        existing = db.query(Coupon).filter(
            Coupon.business_id == business_id,
            Coupon.code == code.upper(),
        ).first()

        if existing:
            return {"success": False, "error": "Coupon code already exists"}

        coupon = Coupon(
            business_id=business_id,
            code=code.upper(),
            name=name,
            description=description,
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount_amount=max_discount_amount,
            minimum_order_amount=minimum_order_amount,
            minimum_quantity=minimum_quantity,
            usage_limit=usage_limit,
            usage_limit_per_customer=usage_limit_per_customer,
            starts_at=starts_at,
            expires_at=expires_at,
            applies_to=applies_to,
            applicable_ids=applicable_ids or [],
            first_order_only=first_order_only,
            is_automatic=is_automatic,
        )
        db.add(coupon)
        db.commit()

        return {
            "success": True,
            "coupon_id": str(coupon.id),
            "code": coupon.code,
        }

    def get_automatic_coupons(
        self,
        db: Session,
        business_id: str,
        subtotal: float,
        customer_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Get automatically applicable coupons."""
        coupons = db.query(Coupon).filter(
            Coupon.business_id == business_id,
            Coupon.is_automatic == True,
            Coupon.status == CouponStatus.ACTIVE,
        ).all()

        applicable = []
        for coupon in coupons:
            if coupon.is_valid and subtotal >= coupon.minimum_order_amount:
                discount = coupon.calculate_discount(subtotal)
                if discount > 0:
                    applicable.append({
                        "coupon_id": str(coupon.id),
                        "code": coupon.code,
                        "name": coupon.name,
                        "discount_amount": discount,
                        "description": coupon.description,
                    })

        # Sort by discount amount (highest first)
        applicable.sort(key=lambda x: x["discount_amount"], reverse=True)
        return applicable

    def get_active_promotions(
        self,
        db: Session,
        business_id: str,
        product_ids: List[str] = None,
        category_ids: List[str] = None,
    ) -> List[Promotion]:
        """Get active promotions."""
        now = datetime.utcnow()
        
        query = db.query(Promotion).filter(
            Promotion.business_id == business_id,
            Promotion.is_active == True,
            Promotion.starts_at <= now,
            Promotion.ends_at >= now,
        )

        promotions = query.all()

        # Filter by product/category if specified
        if product_ids or category_ids:
            filtered = []
            for promo in promotions:
                if product_ids and any(pid in promo.product_ids for pid in product_ids):
                    filtered.append(promo)
                elif category_ids and any(cid in promo.category_ids for cid in category_ids):
                    filtered.append(promo)
                elif not promo.product_ids and not promo.category_ids:
                    # Applies to all
                    filtered.append(promo)
            return filtered

        return promotions

    def calculate_promotion_discount(
        self,
        promotion: Promotion,
        original_price: float,
    ) -> float:
        """Calculate discounted price from a promotion."""
        if promotion.discount_type == DiscountType.PERCENTAGE:
            discount = original_price * (promotion.discount_value / 100)
            return round(original_price - discount, 2)
        elif promotion.discount_type == DiscountType.FIXED_AMOUNT:
            return max(0, round(original_price - promotion.discount_value, 2))
        return original_price

    def get_coupon_stats(
        self,
        db: Session,
        business_id: str,
    ) -> Dict[str, Any]:
        """Get coupon usage statistics."""
        coupons = db.query(Coupon).filter(
            Coupon.business_id == business_id
        ).all()

        total_discount = db.query(func.sum(CouponUsage.discount_applied)).join(
            Coupon
        ).filter(
            Coupon.business_id == business_id
        ).scalar() or 0

        total_uses = db.query(CouponUsage).join(Coupon).filter(
            Coupon.business_id == business_id
        ).count()

        active_coupons = len([c for c in coupons if c.status == CouponStatus.ACTIVE])

        return {
            "total_coupons": len(coupons),
            "active_coupons": active_coupons,
            "total_uses": total_uses,
            "total_discount_given": round(total_discount, 2),
        }


# Global instance
coupon_service = CouponService()
