"""
Loyalty Service - Customer rewards and points management.
Handles points earning, redemption, tiers, and rewards.
"""
import logging
import random
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.loyalty import (
    LoyaltyProgram, LoyaltyTier, LoyaltyReward,
    CustomerLoyalty, LoyaltyTransaction, RewardRedemption,
    TransactionType, RewardType
)
from app.models.customer import Customer

logger = logging.getLogger("devtrack.loyalty")


class LoyaltyService:
    """
    Loyalty program management service.
    Handles points, tiers, rewards, and referrals.
    """

    def _generate_referral_code(self) -> str:
        """Generate unique referral code."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=8))

    def _generate_redemption_code(self) -> str:
        """Generate unique redemption code."""
        chars = string.ascii_uppercase + string.digits
        return f"RWD-{''.join(random.choices(chars, k=6))}"

    async def get_or_create_program(
        self,
        db: Session,
        business_id: str,
    ) -> LoyaltyProgram:
        """Get or create loyalty program for a business."""
        program = db.query(LoyaltyProgram).filter(
            LoyaltyProgram.business_id == business_id
        ).first()

        if not program:
            program = LoyaltyProgram(
                business_id=business_id,
                name="Rewards Program",
                points_per_currency=1.0,
                currency_per_point=0.01,
                min_points_redeem=100,
            )
            db.add(program)
            db.flush()

            # Create default tiers
            tiers = [
                {"name": "Bronze", "color": "#CD7F32", "min_points": 0, "multiplier": 1.0, "order": 1},
                {"name": "Silver", "color": "#C0C0C0", "min_points": 500, "multiplier": 1.25, "order": 2},
                {"name": "Gold", "color": "#FFD700", "min_points": 2000, "multiplier": 1.5, "order": 3},
                {"name": "Platinum", "color": "#E5E4E2", "min_points": 5000, "multiplier": 2.0, "order": 4},
            ]
            for t in tiers:
                tier = LoyaltyTier(
                    program_id=program.id,
                    name=t["name"],
                    color=t["color"],
                    min_points=t["min_points"],
                    points_multiplier=t["multiplier"],
                    tier_order=t["order"],
                )
                db.add(tier)

            db.commit()

        return program

    async def enroll_customer(
        self,
        db: Session,
        business_id: str,
        customer_id: str,
        referred_by_code: str = None,
    ) -> Dict[str, Any]:
        """Enroll a customer in the loyalty program."""
        program = await self.get_or_create_program(db, business_id)

        # Check if already enrolled
        existing = db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if existing:
            return {
                "success": True,
                "already_enrolled": True,
                "customer_loyalty_id": str(existing.id),
            }

        # Get lowest tier
        lowest_tier = db.query(LoyaltyTier).filter(
            LoyaltyTier.program_id == program.id
        ).order_by(LoyaltyTier.tier_order).first()

        # Handle referral
        referred_by = None
        if referred_by_code:
            referrer = db.query(CustomerLoyalty).filter(
                CustomerLoyalty.referral_code == referred_by_code
            ).first()
            if referrer:
                referred_by = referrer.customer_id

        # Create customer loyalty record
        customer_loyalty = CustomerLoyalty(
            customer_id=customer_id,
            program_id=program.id,
            tier_id=lowest_tier.id if lowest_tier else None,
            points_balance=program.signup_bonus_points,
            points_earned_total=program.signup_bonus_points,
            referral_code=self._generate_referral_code(),
            referred_by=referred_by,
        )
        db.add(customer_loyalty)
        db.flush()

        # Record signup bonus if any
        if program.signup_bonus_points > 0:
            transaction = LoyaltyTransaction(
                customer_loyalty_id=customer_loyalty.id,
                transaction_type=TransactionType.BONUS,
                points=program.signup_bonus_points,
                balance_after=program.signup_bonus_points,
                description="Welcome bonus",
            )
            db.add(transaction)

        # Handle referral rewards
        if referred_by and referrer:
            # Reward referrer
            if program.referral_points_referrer > 0:
                await self._add_points(
                    db, referrer.id,
                    program.referral_points_referrer,
                    TransactionType.REFERRAL,
                    "Referral bonus"
                )
                referrer.referral_count += 1

            # Reward referee
            if program.referral_points_referee > 0:
                await self._add_points(
                    db, customer_loyalty.id,
                    program.referral_points_referee,
                    TransactionType.REFERRAL,
                    "Referred signup bonus"
                )

        db.commit()

        return {
            "success": True,
            "customer_loyalty_id": str(customer_loyalty.id),
            "referral_code": customer_loyalty.referral_code,
            "points_balance": customer_loyalty.points_balance,
            "tier": lowest_tier.name if lowest_tier else None,
        }

    async def earn_points(
        self,
        db: Session,
        business_id: str,
        customer_id: str,
        amount: float,
        order_id: str = None,
        description: str = None,
    ) -> Dict[str, Any]:
        """Award points for a purchase."""
        program = await self.get_or_create_program(db, business_id)

        customer_loyalty = db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id,
            CustomerLoyalty.program_id == program.id,
        ).first()

        if not customer_loyalty:
            # Auto-enroll
            result = await self.enroll_customer(db, business_id, customer_id)
            customer_loyalty = db.query(CustomerLoyalty).filter(
                CustomerLoyalty.id == result["customer_loyalty_id"]
            ).first()

        # Get tier multiplier
        tier = db.query(LoyaltyTier).filter(
            LoyaltyTier.id == customer_loyalty.tier_id
        ).first()
        multiplier = tier.points_multiplier if tier else 1.0

        # Calculate points
        points = program.calculate_points(amount, multiplier)

        # Add points
        customer_loyalty.points_balance += points
        customer_loyalty.points_earned_total += points
        customer_loyalty.total_spent += amount
        customer_loyalty.total_orders += 1
        customer_loyalty.last_activity_at = datetime.utcnow()

        # Record transaction
        transaction = LoyaltyTransaction(
            customer_loyalty_id=customer_loyalty.id,
            transaction_type=TransactionType.EARN,
            points=points,
            balance_after=customer_loyalty.points_balance,
            description=description or f"Purchase ${amount:.2f}",
            reference_type="order" if order_id else None,
            reference_id=order_id,
        )
        
        if program.points_expire:
            transaction.expires_at = datetime.utcnow() + timedelta(days=program.points_expire_days)
        
        db.add(transaction)

        # Check for tier upgrade
        await self._check_tier_upgrade(db, customer_loyalty, program)

        db.commit()

        return {
            "success": True,
            "points_earned": points,
            "points_balance": customer_loyalty.points_balance,
            "tier": tier.name if tier else None,
            "multiplier": multiplier,
        }

    async def redeem_points(
        self,
        db: Session,
        customer_id: str,
        points: int,
        reward_id: str = None,
        order_id: str = None,
        description: str = None,
    ) -> Dict[str, Any]:
        """Redeem points for rewards or discount."""
        customer_loyalty = db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if not customer_loyalty:
            return {"success": False, "error": "Customer not enrolled in loyalty program"}

        program = db.query(LoyaltyProgram).filter(
            LoyaltyProgram.id == customer_loyalty.program_id
        ).first()

        if points > customer_loyalty.points_balance:
            return {"success": False, "error": "Insufficient points"}

        if points < program.min_points_redeem:
            return {"success": False, "error": f"Minimum {program.min_points_redeem} points required"}

        # Calculate monetary value
        monetary_value = points * program.currency_per_point

        # Handle reward redemption
        redemption = None
        if reward_id:
            reward = db.query(LoyaltyReward).filter(
                LoyaltyReward.id == reward_id
            ).first()

            if not reward or not reward.is_available:
                return {"success": False, "error": "Reward not available"}

            if reward.points_cost != points:
                points = reward.points_cost

            monetary_value = reward.reward_value or 0

            # Create redemption record
            redemption = RewardRedemption(
                customer_loyalty_id=customer_loyalty.id,
                reward_id=reward_id,
                order_id=order_id,
                points_spent=points,
                reward_value_applied=monetary_value,
                redemption_code=self._generate_redemption_code(),
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
            db.add(redemption)

            reward.times_redeemed += 1

        # Deduct points
        customer_loyalty.points_balance -= points
        customer_loyalty.points_redeemed_total += points
        customer_loyalty.last_activity_at = datetime.utcnow()

        # Record transaction
        transaction = LoyaltyTransaction(
            customer_loyalty_id=customer_loyalty.id,
            transaction_type=TransactionType.REDEEM,
            points=-points,
            balance_after=customer_loyalty.points_balance,
            description=description or "Points redemption",
            reference_type="reward" if reward_id else "order",
            reference_id=reward_id or order_id,
        )
        db.add(transaction)

        db.commit()

        return {
            "success": True,
            "points_redeemed": points,
            "monetary_value": monetary_value,
            "points_balance": customer_loyalty.points_balance,
            "redemption_code": redemption.redemption_code if redemption else None,
        }

    async def _add_points(
        self,
        db: Session,
        customer_loyalty_id: str,
        points: int,
        transaction_type: TransactionType,
        description: str,
    ):
        """Internal method to add points."""
        customer_loyalty = db.query(CustomerLoyalty).filter(
            CustomerLoyalty.id == customer_loyalty_id
        ).first()

        if not customer_loyalty:
            return

        customer_loyalty.points_balance += points
        customer_loyalty.points_earned_total += points

        transaction = LoyaltyTransaction(
            customer_loyalty_id=customer_loyalty_id,
            transaction_type=transaction_type,
            points=points,
            balance_after=customer_loyalty.points_balance,
            description=description,
        )
        db.add(transaction)

    async def _check_tier_upgrade(
        self,
        db: Session,
        customer_loyalty: CustomerLoyalty,
        program: LoyaltyProgram,
    ):
        """Check and upgrade customer tier if eligible."""
        tiers = db.query(LoyaltyTier).filter(
            LoyaltyTier.program_id == program.id
        ).order_by(LoyaltyTier.tier_order.desc()).all()

        for tier in tiers:
            if customer_loyalty.points_earned_total >= tier.min_points:
                if customer_loyalty.tier_id != tier.id:
                    old_tier = customer_loyalty.tier
                    customer_loyalty.tier_id = tier.id
                    customer_loyalty.tier_updated_at = datetime.utcnow()

                    # Tier upgrade bonus
                    bonus = int(tier.min_points * 0.1)  # 10% of threshold as bonus
                    if bonus > 0:
                        await self._add_points(
                            db, customer_loyalty.id,
                            bonus,
                            TransactionType.TIER_BONUS,
                            f"Tier upgrade to {tier.name}"
                        )
                break

    def get_customer_loyalty_status(
        self,
        db: Session,
        customer_id: str,
    ) -> Dict[str, Any]:
        """Get customer's loyalty status."""
        customer_loyalty = db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if not customer_loyalty:
            return {"enrolled": False}

        tier = db.query(LoyaltyTier).filter(
            LoyaltyTier.id == customer_loyalty.tier_id
        ).first()

        # Get next tier
        next_tier = None
        if tier:
            next_tier = db.query(LoyaltyTier).filter(
                LoyaltyTier.program_id == customer_loyalty.program_id,
                LoyaltyTier.tier_order > tier.tier_order
            ).order_by(LoyaltyTier.tier_order).first()

        # Calculate progress to next tier
        progress = 100
        points_to_next = 0
        if next_tier:
            points_to_next = next_tier.min_points - customer_loyalty.points_earned_total
            if points_to_next > 0:
                progress = int((customer_loyalty.points_earned_total / next_tier.min_points) * 100)

        return {
            "enrolled": True,
            "points_balance": customer_loyalty.points_balance,
            "points_earned_total": customer_loyalty.points_earned_total,
            "tier": tier.name if tier else None,
            "tier_color": tier.color if tier else None,
            "tier_multiplier": tier.points_multiplier if tier else 1.0,
            "next_tier": next_tier.name if next_tier else None,
            "points_to_next_tier": max(0, points_to_next),
            "progress_to_next_tier": min(100, progress),
            "referral_code": customer_loyalty.referral_code,
            "referral_count": customer_loyalty.referral_count,
            "total_spent": customer_loyalty.total_spent,
            "total_orders": customer_loyalty.total_orders,
        }

    def get_available_rewards(
        self,
        db: Session,
        program_id: str,
        customer_points: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get available rewards for a program."""
        rewards = db.query(LoyaltyReward).filter(
            LoyaltyReward.program_id == program_id,
            LoyaltyReward.is_active == True,
        ).all()

        return [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "image_url": r.image_url,
                "points_cost": r.points_cost,
                "reward_type": r.reward_type.value,
                "reward_value": r.reward_value,
                "is_available": r.is_available,
                "can_redeem": customer_points >= r.points_cost and r.is_available,
            }
            for r in rewards
        ]


# Global instance
loyalty_service = LoyaltyService()
