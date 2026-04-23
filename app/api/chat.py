"""
Public Chat API for the web widget.
Does NOT require JWT authentication - uses business slug for identification.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.db.session import get_db
from app.models.business import Business
from app.models.customer import Customer
from app.models.conversation import Conversation, Message, ConversationStatus, MessageSender
from app.schemas.schemas import ChatMessage
from app.services.ai_service import ai_service
from app.services.rag_service import rag_service

router = APIRouter(prefix="/chat", tags=["Public Chat"])


@router.post("/message")
async def public_chat_message(
    data: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    Public endpoint for the web chat widget.
    Processes a customer message and returns an AI response.
    No authentication required - identified by business slug.
    """
    # Find business by slug
    business = db.query(Business).filter(Business.slug == data.business_slug).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Find or create customer
    customer = None
    if data.customer_id:
        customer = db.query(Customer).filter(
            Customer.id == data.customer_id,
            Customer.business_id == business.id
        ).first()
    
    if not customer:
        customer = Customer(
            business_id=business.id,
            name="Web Visitor",
            channel=data.channel,
        )
        db.add(customer)
        db.flush()
    
    # Find or create conversation
    conversation = db.query(Conversation).filter(
        Conversation.customer_id == customer.id,
        Conversation.business_id == business.id,
        Conversation.status.in_([ConversationStatus.ACTIVE, ConversationStatus.AI_HANDLING])
    ).first()
    
    if not conversation:
        conversation = Conversation(
            business_id=business.id,
            customer_id=customer.id,
            channel=data.channel,
            status=ConversationStatus.AI_HANDLING,
        )
        db.add(conversation)
        db.flush()
    
    # Save customer message
    customer_message = Message(
        conversation_id=conversation.id,
        content=data.message,
        sender_type=MessageSender.CUSTOMER,
        sender_id=customer.id,
    )
    db.add(customer_message)
    
    # Get RAG context
    context = rag_service.get_context(data.message, str(business.id))
    
    # Get conversation history
    history = []
    for msg in conversation.messages[-10:]:
        history.append({
            "role": msg.sender_type.value,
            "content": msg.content
        })
    
    # Process through AI
    ai_result = await ai_service.process_message(
        message=data.message,
        persona=conversation.ai_persona or "general",
        business_name=business.name,
        business_type=business.business_type,
        ai_tone=business.ai_tone,
        ai_language=business.ai_language,
        conversation_history=history,
        context=context
    )
    
    # Save AI response
    ai_message = Message(
        conversation_id=conversation.id,
        content=ai_result["response_text"],
        sender_type=MessageSender.AI,
        ai_intent=ai_result["intent"],
        ai_confidence=80,
        ai_action_taken=ai_result["action"],
    )
    db.add(ai_message)
    
    # Update timestamps
    conversation.last_message_at = datetime.utcnow()
    conversation.sentiment_score = ai_result["sentiment"]
    customer.last_seen = datetime.utcnow()
    
    db.commit()
    
    return {
        "response": ai_result["response_text"],
        "intent": ai_result["intent"],
        "sentiment": ai_result["sentiment"],
        "action": ai_result["action"],
        "conversation_id": str(conversation.id),
        "customer_id": str(customer.id),
    }


@router.get("/business/{slug}")
def get_business_info(slug: str, db: Session = Depends(get_db)):
    """Get public business info for the chat widget."""
    business = db.query(Business).filter(Business.slug == slug).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {
        "name": business.name,
        "logo_url": business.logo_url,
        "primary_color": business.primary_color,
        "secondary_color": business.secondary_color,
        "welcome_message": business.welcome_message,
        "business_type": business.business_type,
    }
