"""
Models package initialization.
Import all models to ensure they're registered with SQLAlchemy.
"""
from app.models.user import User, UserRole
from app.models.business import Business, BusinessModule
from app.models.customer import Customer
from app.models.conversation import Conversation, Message
from app.models.order import Order, OrderItem
from app.models.booking import Booking
from app.models.product import Product, Category
from app.models.service import Service
from app.models.document import Document, DocumentChunk
from app.models.workflow import Workflow
from app.models.analytics import AnalyticsEvent
from app.models.module import ModuleDefinition
from app.models.notification import Notification
from app.models.audit import AuditLog, StaffInvitation

# Enterprise models
from app.models.payment import Payment, Refund, CustomerPaymentMethod
from app.models.coupon import Coupon, CouponUsage, Promotion
from app.models.inventory import (
    Supplier, ProductInventory, StockMovement, 
    PurchaseOrder, PurchaseOrderItem, InventoryAlert
)
from app.models.loyalty import (
    LoyaltyProgram, LoyaltyTier, LoyaltyReward,
    CustomerLoyalty, LoyaltyTransaction, RewardRedemption
)
from app.models.team import (
    Role, Permission, TeamMember, TeamInvite, 
    ActivityLog, Location
)
from app.models.campaign import (
    Campaign, EmailTemplate, CampaignRecipient,
    CampaignLink, Unsubscribe
)

__all__ = [
    # Core models
    "User", "UserRole",
    "Business", "BusinessModule",
    "Customer",
    "Conversation", "Message",
    "Order", "OrderItem",
    "Booking",
    "Product", "Category",
    "Service",
    "Document", "DocumentChunk",
    "Workflow",
    "AnalyticsEvent",
    "ModuleDefinition",
    "Notification",
    "AuditLog", "StaffInvitation",
    
    # Payment models
    "Payment", "Refund", "CustomerPaymentMethod",
    
    # Coupon models
    "Coupon", "CouponUsage", "Promotion",
    
    # Inventory models
    "Supplier", "ProductInventory", "StockMovement",
    "PurchaseOrder", "PurchaseOrderItem", "InventoryAlert",
    
    # Loyalty models
    "LoyaltyProgram", "LoyaltyTier", "LoyaltyReward",
    "CustomerLoyalty", "LoyaltyTransaction", "RewardRedemption",
    
    # Team models
    "Role", "Permission", "TeamMember", "TeamInvite",
    "ActivityLog", "Location",
    
    # Campaign models
    "Campaign", "EmailTemplate", "CampaignRecipient",
    "CampaignLink", "Unsubscribe",
]
