"""
Payment Service - Stripe Integration.
Handles payment processing, refunds, checkout sessions, and webhooks.
"""
import logging
import uuid
import random
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.payment import Payment, Refund, PaymentStatus, RefundStatus, PaymentMethod

logger = logging.getLogger("devtrack.payments")

# Try to import Stripe
try:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY if hasattr(settings, 'STRIPE_SECRET_KEY') else None
    STRIPE_AVAILABLE = bool(stripe.api_key)
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None


class PaymentService:
    """
    Payment service with Stripe integration.
    Supports card payments, checkout sessions, refunds, and webhooks.
    """

    def __init__(self):
        self.stripe_available = STRIPE_AVAILABLE

    def _generate_payment_number(self) -> str:
        """Generate unique payment number."""
        chars = string.ascii_uppercase + string.digits
        return f"PAY-{''.join(random.choices(chars, k=8))}"

    def _generate_refund_number(self) -> str:
        """Generate unique refund number."""
        chars = string.ascii_uppercase + string.digits
        return f"REF-{''.join(random.choices(chars, k=8))}"

    async def create_checkout_session(
        self,
        db,
        business_id: str,
        order_id: str,
        amount: float,
        currency: str = "USD",
        customer_id: str = None,
        customer_email: str = None,
        success_url: str = None,
        cancel_url: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for an order.
        Returns checkout URL for customer to complete payment.
        """
        from app.models.order import Order
        
        # Get order details
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "error": "Order not found"}

        # Create payment record
        payment = Payment(
            business_id=business_id,
            customer_id=customer_id,
            order_id=order_id,
            payment_number=self._generate_payment_number(),
            amount=amount,
            currency=currency.upper(),
            status=PaymentStatus.PENDING,
            method=PaymentMethod.STRIPE,
            extra_metadata=metadata or {},
        )
        db.add(payment)
        db.flush()

        if self.stripe_available:
            try:
                # Build line items from order
                line_items = []
                for item in order.items:
                    line_items.append({
                        "price_data": {
                            "currency": currency.lower(),
                            "unit_amount": int(item.unit_price * 100),  # Stripe uses cents
                            "product_data": {
                                "name": item.name,
                            },
                        },
                        "quantity": item.quantity,
                    })

                # Add tax as separate line item if present
                if order.tax > 0:
                    line_items.append({
                        "price_data": {
                            "currency": currency.lower(),
                            "unit_amount": int(order.tax * 100),
                            "product_data": {"name": "Tax"},
                        },
                        "quantity": 1,
                    })

                # Create Stripe checkout session
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    success_url=success_url or f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=cancel_url or f"{settings.FRONTEND_URL}/checkout/cancel",
                    customer_email=customer_email,
                    metadata={
                        "payment_id": str(payment.id),
                        "order_id": str(order_id),
                        "business_id": str(business_id),
                        **(metadata or {}),
                    },
                )

                # Update payment with Stripe session
                payment.stripe_payment_intent_id = session.payment_intent
                payment.checkout_url = session.url
                payment.checkout_expires_at = datetime.utcnow() + timedelta(hours=24)
                
                db.commit()

                return {
                    "success": True,
                    "payment_id": str(payment.id),
                    "checkout_url": session.url,
                    "session_id": session.id,
                }

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {e}")
                payment.status = PaymentStatus.FAILED
                payment.failure_message = str(e)
                db.commit()
                return {"success": False, "error": str(e)}
        else:
            # Demo mode - generate mock checkout URL
            payment.checkout_url = f"/demo/checkout/{payment.id}"
            payment.checkout_expires_at = datetime.utcnow() + timedelta(hours=24)
            db.commit()
            
            return {
                "success": True,
                "payment_id": str(payment.id),
                "checkout_url": payment.checkout_url,
                "demo_mode": True,
            }

    async def create_payment_intent(
        self,
        db,
        business_id: str,
        amount: float,
        currency: str = "USD",
        order_id: str = None,
        customer_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe PaymentIntent for custom payment flows.
        Returns client_secret for frontend Stripe.js integration.
        """
        payment = Payment(
            business_id=business_id,
            customer_id=customer_id,
            order_id=order_id,
            payment_number=self._generate_payment_number(),
            amount=amount,
            currency=currency.upper(),
            status=PaymentStatus.PENDING,
            method=PaymentMethod.STRIPE,
            extra_metadata=metadata or {},
        )
        db.add(payment)
        db.flush()

        if self.stripe_available:
            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),
                    currency=currency.lower(),
                    metadata={
                        "payment_id": str(payment.id),
                        "business_id": str(business_id),
                        **(metadata or {}),
                    },
                )

                payment.stripe_payment_intent_id = intent.id
                db.commit()

                return {
                    "success": True,
                    "payment_id": str(payment.id),
                    "client_secret": intent.client_secret,
                    "payment_intent_id": intent.id,
                }

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {e}")
                payment.status = PaymentStatus.FAILED
                payment.failure_message = str(e)
                db.commit()
                return {"success": False, "error": str(e)}
        else:
            db.commit()
            return {
                "success": True,
                "payment_id": str(payment.id),
                "client_secret": f"demo_secret_{payment.id}",
                "demo_mode": True,
            }

    async def confirm_payment(
        self,
        db,
        payment_id: str,
        stripe_payment_intent_id: str = None,
    ) -> Dict[str, Any]:
        """
        Confirm a payment has been completed.
        Called after successful Stripe webhook or manual confirmation.
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return {"success": False, "error": "Payment not found"}

        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = datetime.utcnow()
        
        if stripe_payment_intent_id:
            payment.stripe_payment_intent_id = stripe_payment_intent_id

        # Update order payment status
        if payment.order_id:
            from app.models.order import Order, OrderStatus
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                order.payment_status = "paid"
                order.payment_id = str(payment.id)
                if order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.CONFIRMED

        db.commit()

        return {
            "success": True,
            "payment_id": str(payment.id),
            "status": payment.status.value,
        }

    async def process_refund(
        self,
        db,
        payment_id: str,
        amount: float = None,
        reason: str = None,
        initiated_by: str = None,
    ) -> Dict[str, Any]:
        """
        Process a refund for a payment.
        Supports partial refunds.
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return {"success": False, "error": "Payment not found"}

        if payment.status != PaymentStatus.SUCCEEDED:
            return {"success": False, "error": "Payment must be succeeded to refund"}

        # Default to full refund
        refund_amount = amount if amount else payment.net_amount
        
        if refund_amount > payment.net_amount:
            return {"success": False, "error": "Refund amount exceeds available amount"}

        # Create refund record
        refund = Refund(
            payment_id=payment.id,
            refund_number=self._generate_refund_number(),
            amount=refund_amount,
            reason=reason,
            status=RefundStatus.PENDING,
            initiated_by=initiated_by,
        )
        db.add(refund)
        db.flush()

        if self.stripe_available and payment.stripe_payment_intent_id:
            try:
                stripe_refund = stripe.Refund.create(
                    payment_intent=payment.stripe_payment_intent_id,
                    amount=int(refund_amount * 100),
                    reason="requested_by_customer" if not reason else None,
                )

                refund.stripe_refund_id = stripe_refund.id
                refund.status = RefundStatus.SUCCEEDED
                refund.processed_at = datetime.utcnow()

            except stripe.error.StripeError as e:
                logger.error(f"Stripe refund error: {e}")
                refund.status = RefundStatus.FAILED
                db.commit()
                return {"success": False, "error": str(e)}
        else:
            # Demo mode
            refund.status = RefundStatus.SUCCEEDED
            refund.processed_at = datetime.utcnow()

        # Update payment status
        if refund_amount >= payment.net_amount:
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PARTIALLY_REFUNDED

        db.commit()

        return {
            "success": True,
            "refund_id": str(refund.id),
            "refund_number": refund.refund_number,
            "amount": refund_amount,
            "status": refund.status.value,
        }

    async def handle_webhook(self, db, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Handle Stripe webhook events.
        """
        if not self.stripe_available:
            return {"success": False, "error": "Stripe not configured"}

        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        if not webhook_secret:
            return {"success": False, "error": "Webhook secret not configured"}

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            return {"success": False, "error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            return {"success": False, "error": "Invalid signature"}

        # Handle the event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            payment_id = session.get("metadata", {}).get("payment_id")
            if payment_id:
                await self.confirm_payment(db, payment_id, session.get("payment_intent"))

        elif event["type"] == "payment_intent.succeeded":
            intent = event["data"]["object"]
            payment_id = intent.get("metadata", {}).get("payment_id")
            if payment_id:
                await self.confirm_payment(db, payment_id, intent["id"])

        elif event["type"] == "payment_intent.payment_failed":
            intent = event["data"]["object"]
            payment_id = intent.get("metadata", {}).get("payment_id")
            if payment_id:
                payment = db.query(Payment).filter(Payment.id == payment_id).first()
                if payment:
                    payment.status = PaymentStatus.FAILED
                    payment.failure_code = intent.get("last_payment_error", {}).get("code")
                    payment.failure_message = intent.get("last_payment_error", {}).get("message")
                    db.commit()

        return {"success": True, "event_type": event["type"]}

    def get_payment_stats(self, db, business_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get payment statistics for a business.
        """
        from sqlalchemy import func
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        payments = db.query(Payment).filter(
            Payment.business_id == business_id,
            Payment.created_at >= start_date
        ).all()

        succeeded = [p for p in payments if p.status == PaymentStatus.SUCCEEDED]
        failed = [p for p in payments if p.status == PaymentStatus.FAILED]

        return {
            "total_payments": len(payments),
            "successful_payments": len(succeeded),
            "failed_payments": len(failed),
            "total_revenue": sum(p.amount for p in succeeded),
            "total_refunded": sum(p.refunded_amount for p in succeeded),
            "net_revenue": sum(p.net_amount for p in succeeded),
            "success_rate": round(len(succeeded) / len(payments) * 100, 2) if payments else 0,
            "period_days": days,
        }


# Global instance
payment_service = PaymentService()
