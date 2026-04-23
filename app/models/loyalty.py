"""
Loyalty program models.
Supports points earning, redemption, tiers, and rewards.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class TransactionType(str, enum.Enum):
    """Loyalty points transaction type."""
    EARN = "earn"
    REDEEM = "redeem"
    EXPIRE = "expire"
    ADJUST = "adjust"
    BONUS = "bonus"
    REFERRAL = "referral"
    TIER_BONUS = "tier_bonus"


class RewardType(str, enum.Enum):
    """Type of loyalty reward."""
    DISCOUNT_PERCENTAGE = "discount_percentage"
    DISCOUNT_FIXED = "discount_fixed"
    FREE_PRODUCT = "free_product"
    FREE_SHIPPING = "free_shipping"
    POINTS_MULTIPLIER = "points_multiplier"
    EXCLUSIVE_ACCESS = "exclusive_access"


class LoyaltyProgram(Base):
    """
    Business loyalty program configuration.
    """
    __tablename__ = "loyalty_programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, unique=True)
    
    # Program settings
    name = Column(String(255), default="Rewards Program")
    description = Column(Text, nullable=True)
    
    # Points configuration
    points_per_currency = Column(Float, default=1.0)  # Points earned per $1 spent
    currency_per_point = Column(Float, default=0.01)  # Value of 1 point in $
    min_points_redeem = Column(Integer, default=100)  # Minimum points to redeem
    
    # Points expiry
    points_expire = Column(Boolean, default=False)
    points_expire_days = Column(Integer, default=365)  # Days until expiry
    
    # Signup bonus
    signup_bonus_points = Column(Integer, default=0)
    
    # Referral program
    referral_points_referrer = Column(Integer, default=0)
    referral_points_referee = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="loyalty_program")
    tiers = relationship("LoyaltyTier", back_populates="program", cascade="all, delete-orphan")
    rewards = relationship("LoyaltyReward", back_populates="program", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LoyaltyProgram {self.name}>"

    def calculate_points(self, amount: float, tier_multiplier: float = 1.0) -> int:
        """Calculate points earned for a purchase amount."""
        base_points = int(amount * self.points_per_currency)
        return int(base_points * tier_multiplier)


class LoyaltyTier(Base):
    """
    Loyalty program tiers (e.g., Bronze, Silver, Gold, Platinum).
    """
    __tablename__ = "loyalty_tiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("loyalty_programs.id"), nullable=False)
    
    # Tier details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), default="#888888")  # Badge color
    icon = Column(String(50), nullable=True)
    
    # Qualification
    min_points = Column(Integer, default=0)  # Points needed to reach tier
    min_spent = Column(Float, default=0)  # Or total spent
    
    # Benefits
    points_multiplier = Column(Float, default=1.0)  # 1.5x, 2x points earning
    discount_percentage = Column(Float, default=0)  # Permanent discount
    free_shipping = Column(Boolean, default=False)
    priority_support = Column(Boolean, default=False)
    exclusive_access = Column(Boolean, default=False)
    
    # Custom benefits (JSON)
    extra_benefits = Column(JSON, default=list)
    
    # Order (1 = lowest tier)
    tier_order = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    program = relationship("LoyaltyProgram", back_populates="tiers")

    def __repr__(self):
        return f"<LoyaltyTier {self.name}>"


class LoyaltyReward(Base):
    """
    Redeemable rewards in the loyalty program.
    """
    __tablename__ = "loyalty_rewards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("loyalty_programs.id"), nullable=False)
    
    # Reward details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # Cost
    points_cost = Column(Integer, nullable=False)
    
    # Reward type and value
    reward_type = Column(SQLEnum(RewardType), nullable=False)
    reward_value = Column(Float, nullable=True)  # Discount amount or percentage
    reward_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    
    # Restrictions
    min_tier_id = Column(UUID(as_uuid=True), ForeignKey("loyalty_tiers.id"), nullable=True)
    min_order_amount = Column(Float, default=0)
    
    # Availability
    stock_quantity = Column(Integer, nullable=True)  # Null = unlimited
    times_redeemed = Column(Integer, default=0)
    
    # Validity
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    program = relationship("LoyaltyProgram", back_populates="rewards")

    def __repr__(self):
        return f"<LoyaltyReward {self.name} - {self.points_cost} pts>"

    @property
    def is_available(self) -> bool:
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        if self.stock_quantity is not None and self.times_redeemed >= self.stock_quantity:
            return False
        return True


class CustomerLoyalty(Base):
    """
    Customer's loyalty status and points balance.
    """
    __tablename__ = "customer_loyalty"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, unique=True)
    program_id = Column(UUID(as_uuid=True), ForeignKey("loyalty_programs.id"), nullable=False)
    tier_id = Column(UUID(as_uuid=True), ForeignKey("loyalty_tiers.id"), nullable=True)
    
    # Points balance
    points_balance = Column(Integer, default=0)
    points_earned_total = Column(Integer, default=0)
    points_redeemed_total = Column(Integer, default=0)
    points_expired_total = Column(Integer, default=0)
    
    # Spending
    total_spent = Column(Float, default=0)
    total_orders = Column(Integer, default=0)
    
    # Referral tracking
    referral_code = Column(String(20), unique=True, nullable=True)
    referred_by = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    referral_count = Column(Integer, default=0)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    tier_updated_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", backref="loyalty", foreign_keys=[customer_id])
    program = relationship("LoyaltyProgram", backref="members")
    tier = relationship("LoyaltyTier", backref="members")
    transactions = relationship("LoyaltyTransaction", back_populates="customer_loyalty", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CustomerLoyalty {self.customer_id} - {self.points_balance} pts>"


class LoyaltyTransaction(Base):
    """
    Individual loyalty points transactions.
    """
    __tablename__ = "loyalty_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_loyalty_id = Column(UUID(as_uuid=True), ForeignKey("customer_loyalty.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    points = Column(Integer, nullable=False)  # Positive for earn, negative for redeem
    balance_after = Column(Integer, nullable=False)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Reference
    reference_type = Column(String(50), nullable=True)  # order, reward, referral
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Expiry tracking
    expires_at = Column(DateTime, nullable=True)
    is_expired = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer_loyalty = relationship("CustomerLoyalty", back_populates="transactions")

    def __repr__(self):
        return f"<LoyaltyTransaction {self.transaction_type} - {self.points} pts>"


class RewardRedemption(Base):
    """
    Tracks reward redemptions by customers.
    """
    __tablename__ = "reward_redemptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_loyalty_id = Column(UUID(as_uuid=True), ForeignKey("customer_loyalty.id"), nullable=False)
    reward_id = Column(UUID(as_uuid=True), ForeignKey("loyalty_rewards.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    # Redemption details
    points_spent = Column(Integer, nullable=False)
    reward_value_applied = Column(Float, nullable=True)
    
    # Redemption code (for manual verification)
    redemption_code = Column(String(20), unique=True, nullable=True)
    
    # Status
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    
    # Validity
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer_loyalty = relationship("CustomerLoyalty", backref="redemptions")
    reward = relationship("LoyaltyReward", backref="redemptions")
    order = relationship("Order", backref="reward_redemptions")

    def __repr__(self):
        return f"<RewardRedemption {self.reward_id} - {self.points_spent} pts>"
