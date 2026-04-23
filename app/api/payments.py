"""
Payment API endpoints.
Handles payment processing, checkout sessions, refunds, and webhooks.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.payment_service import payment_service
from app.models.payment import Payment, Refund, PaymentStatus


router = APIRouter(prefix="/payments", tags=["Payments"])


# ═══════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════

class CheckoutSessionCreate(BaseModel):
    order_id: str
    customer_email: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentIntentCreate(BaseModel):
    amount: float
    currency: str = "USD"
    order_id: Optional[str] = None
    customer_id: Optional[str] = None


class RefundCreate(BaseModel):
    amount: Optional[float] = None
    reason: Optional[str] = None


class PaymentResponse(BaseModel):
    id: str
    payment_number: str
    amount: float
    currency: str
    status: str
    method: str
    order_id: Optional[str]
    checkout_url: Optional[str]
    card_brand: Optional[str]
    card_last4: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class RefundResponse(BaseModel):
    id: str
    refund_number: str
    amount: float
    status: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/checkout-session")
async def create_checkout_session(
    data: CheckoutSessionCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe checkout session for an order.
    Returns a checkout URL for the customer.
    """
    result = await payment_service.create_checkout_session(
        db=db,
        business_id=str(current_user["business_id"]),
        order_id=data.order_id,
        amount=0,  # Will be calculated from order
        customer_email=data.customer_email,
        success_url=data.success_url,
        cancel_url=data.cancel_url,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/payment-intent")
async def create_payment_intent(
    data: PaymentIntentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe PaymentIntent for custom payment flows.
    Returns client_secret for Stripe.js integration.
    """
    result = await payment_service.create_payment_intent(
        db=db,
        business_id=str(current_user["business_id"]),
        amount=data.amount,
        currency=data.currency,
        order_id=data.order_id,
        customer_id=data.customer_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/", response_model=List[PaymentResponse])
def list_payments(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all payments for the business."""
    query = db.query(Payment).filter(
        Payment.business_id == current_user["business_id"]
    )
    
    if status:
        query = query.filter(Payment.status == status)
    
    payments = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        PaymentResponse(
            id=str(p.id),
            payment_number=p.payment_number,
            amount=p.amount,
            currency=p.currency,
            status=p.status.value,
            method=p.method.value,
            order_id=str(p.order_id) if p.order_id else None,
            checkout_url=p.checkout_url,
            card_brand=p.card_brand,
            card_last4=p.card_last4,
            created_at=p.created_at,
            paid_at=p.paid_at,
        )
        for p in payments
    ]


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific payment."""
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.business_id == current_user["business_id"]
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentResponse(
        id=str(payment.id),
        payment_number=payment.payment_number,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status.value,
        method=payment.method.value,
        order_id=str(payment.order_id) if payment.order_id else None,
        checkout_url=payment.checkout_url,
        card_brand=payment.card_brand,
        card_last4=payment.card_last4,
        created_at=payment.created_at,
        paid_at=payment.paid_at,
    )


@router.post("/{payment_id}/confirm")
async def confirm_payment(
    payment_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually confirm a payment (for cash/manual payments)."""
    result = await payment_service.confirm_payment(db, str(payment_id))
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: UUID,
    data: RefundCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Process a refund for a payment."""
    result = await payment_service.process_refund(
        db=db,
        payment_id=str(payment_id),
        amount=data.amount,
        reason=data.reason,
        initiated_by=str(current_user["user_id"]),
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{payment_id}/refunds", response_model=List[RefundResponse])
def list_refunds(
    payment_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List refunds for a payment."""
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.business_id == current_user["business_id"]
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return [
        RefundResponse(
            id=str(r.id),
            refund_number=r.refund_number,
            amount=r.amount,
            status=r.status.value,
            reason=r.reason,
            created_at=r.created_at,
        )
        for r in payment.refunds
    ]


@router.get("/stats/summary")
def get_payment_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get payment statistics for the business."""
    return payment_service.get_payment_stats(
        db,
        str(current_user["business_id"]),
        days
    )


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    Verifies signature and processes payment events.
    """
    payload = await request.body()
    
    result = await payment_service.handle_webhook(db, payload, stripe_signature)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return {"received": True, "event_type": result.get("event_type")}
