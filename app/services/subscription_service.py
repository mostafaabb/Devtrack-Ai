"""
Subscription & Plan Enforcement Service.
Enforces limits based on business plan (free, starter, pro, enterprise).
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
import logging

from app.models.business import Business
from app.models.customer import Customer
from app.models.order import Order
from app.models.conversation import Conversation, Message, MessageSender
from app.models.user import User
from app.models.document import Document

logger = logging.getLogger("devtrack.subscription")


# Plan definitions with limits
PLAN_LIMITS = {
    "free": {
        "max_customers": 50,
        "max_ai_messages_per_month": 100,
        "max_users": 1,
        "max_channels": 1,
        "max_products": 20,
        "max_documents": 3,
        "max_workflows": 2,
        "max_upload_mb": 10,
        "features": ["web_chat", "basic_analytics"],
    },
    "starter": {
        "max_customers": 500,
        "max_ai_messages_per_month": 1000,
        "max_users": 3,
        "max_channels": 2,
        "max_products": 200,
        "max_documents": 20,
        "max_workflows": 10,
        "max_upload_mb": 50,
        "features": ["web_chat", "whatsapp", "email_notifications", "analytics", "data_export"],
    },
    "pro": {
        "max_customers": -1,  # unlimited
        "max_ai_messages_per_month": 5000,
        "max_users": 10,
        "max_channels": -1,
        "max_products": -1,
        "max_documents": 100,
        "max_workflows": 50,
        "max_upload_mb": 200,
        "features": ["web_chat", "whatsapp", "instagram", "messenger", "email_notifications",
                      "analytics", "advanced_analytics", "data_export", "automation", "api_access"],
    },
    "enterprise": {
        "max_customers": -1,
        "max_ai_messages_per_month": -1,
        "max_users": -1,
        "max_channels": -1,
        "max_products": -1,
        "max_documents": -1,
        "max_workflows": -1,
        "max_upload_mb": 500,
        "features": ["web_chat", "whatsapp", "instagram", "messenger", "email_notifications",
                      "analytics", "advanced_analytics", "data_export", "automation", "api_access",
                      "custom_ai_training", "priority_support", "white_label", "sla"],
    },
}


class SubscriptionService:
    """Enforces plan limits and tracks usage."""

    def get_plan_limits(self, plan: str) -> Dict[str, Any]:
        """Get limits for a specific plan."""
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    def get_usage(self, db: Session, business_id: str) -> Dict[str, int]:
        """Get current resource usage for a business."""
        from datetime import datetime, timedelta

        # Count resources
        customer_count = db.query(func.count(Customer.id)).filter(
            Customer.business_id == business_id
        ).scalar() or 0

        user_count = db.query(func.count(User.id)).filter(
            User.business_id == business_id
        ).scalar() or 0

        product_count = db.query(func.count()).select_from(
            __import__('app.models.product', fromlist=['Product']).Product
        ).filter_by(business_id=business_id).scalar() or 0

        document_count = db.query(func.count(Document.id)).filter(
            Document.business_id == business_id
        ).scalar() or 0

        # AI messages this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ai_messages_this_month = db.query(func.count(Message.id)).join(
            Conversation, Message.conversation_id == Conversation.id
        ).filter(
            Conversation.business_id == business_id,
            Message.sender == MessageSender.AI,
            Message.created_at >= month_start
        ).scalar() or 0

        return {
            "customers": customer_count,
            "users": user_count,
            "products": product_count,
            "documents": document_count,
            "ai_messages_this_month": ai_messages_this_month,
        }

    def check_limit(self, db: Session, business_id: str, resource: str) -> Dict[str, Any]:
        """
        Check if a specific resource is within plan limits.
        
        Returns:
            {
                "allowed": True/False,
                "current": current_count,
                "limit": max_allowed (-1 = unlimited),
                "plan": "free"
            }
        """
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return {"allowed": False, "reason": "Business not found"}

        plan = business.subscription_plan or "free"
        limits = self.get_plan_limits(plan)
        usage = self.get_usage(db, business_id)

        resource_map = {
            "customers": ("max_customers", usage.get("customers", 0)),
            "users": ("max_users", usage.get("users", 0)),
            "products": ("max_products", usage.get("products", 0)),
            "documents": ("max_documents", usage.get("documents", 0)),
            "ai_messages": ("max_ai_messages_per_month", usage.get("ai_messages_this_month", 0)),
        }

        if resource not in resource_map:
            return {"allowed": True, "reason": "Unknown resource — allowing"}

        limit_key, current = resource_map[resource]
        max_limit = limits.get(limit_key, -1)

        if max_limit == -1:  # unlimited
            return {"allowed": True, "current": current, "limit": -1, "plan": plan}

        allowed = current < max_limit
        return {
            "allowed": allowed,
            "current": current,
            "limit": max_limit,
            "plan": plan,
            "upgrade_message": f"You've reached the {resource} limit ({max_limit}) for the {plan} plan. Upgrade to add more."
            if not allowed else None,
        }

    def has_feature(self, db: Session, business_id: str, feature: str) -> bool:
        """Check if a business plan includes a specific feature."""
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return False

        plan = business.subscription_plan or "free"
        limits = self.get_plan_limits(plan)
        return feature in limits.get("features", [])

    def get_subscription_info(self, db: Session, business_id: str) -> Dict[str, Any]:
        """Get full subscription info including usage vs limits."""
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return {"plan": "free", "error": "Business not found"}

        plan = business.subscription_plan or "free"
        limits = self.get_plan_limits(plan)
        usage = self.get_usage(db, business_id)

        over_limits = []
        resource_checks = {
            "customers": ("max_customers", usage.get("customers", 0)),
            "users": ("max_users", usage.get("users", 0)),
            "ai_messages": ("max_ai_messages_per_month", usage.get("ai_messages_this_month", 0)),
        }

        for resource_name, (limit_key, current_val) in resource_checks.items():
            max_val = limits.get(limit_key, -1)
            if max_val != -1 and current_val >= max_val:
                over_limits.append(resource_name)

        return {
            "plan": plan,
            "limits": limits,
            "usage": usage,
            "is_over_limit": len(over_limits) > 0,
            "upgrade_required": over_limits,
        }


# Global instance
subscription_service = SubscriptionService()
