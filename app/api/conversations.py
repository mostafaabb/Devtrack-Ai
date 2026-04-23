"""
Conversations and Chat API routes.
Handles real-time messaging, AI auto-replies, and human takeover.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.conversation import Conversation, Message, ConversationStatus, MessageSender
from app.models.customer import Customer
from app.models.business import Business
from app.schemas.schemas import (
    ConversationCreate, ConversationResponse, MessageCreate, MessageResponse,
    CustomerCreate, CustomerResponse
)
from app.services.ai_service import ai_service
from app.services.rag_service import rag_service
from app.services.automation_service import automation_engine

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/", response_model=List[ConversationResponse])
def list_conversations(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all conversations for the business, with optional status filter."""
    query = db.query(Conversation).filter(
        Conversation.business_id == current_user["business_id"]
    ).options(
        joinedload(Conversation.customer),
        joinedload(Conversation.messages)
    )
    
    if status:
        query = query.filter(Conversation.status == status)
    
    conversations = query.order_by(
        Conversation.last_message_at.desc()
    ).offset(offset).limit(limit).all()
    
    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with all messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.business_id == current_user["business_id"]
    ).options(
        joinedload(Conversation.customer),
        joinedload(Conversation.messages)
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.post("/", response_model=ConversationResponse)
def create_conversation(
    data: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation with a customer."""
    # Verify customer belongs to business
    customer = db.query(Customer).filter(
        Customer.id == data.customer_id,
        Customer.business_id == current_user["business_id"]
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    conversation = Conversation(
        business_id=current_user["business_id"],
        customer_id=data.customer_id,
        channel=data.channel,
        subject=data.subject,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return conversation


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message in a conversation.
    If sender is 'customer', AI will auto-reply (if enabled).
    If sender is 'staff', it's a human response.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.business_id == current_user["business_id"]
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create the message
    sender_type = MessageSender(data.sender_type) if data.sender_type in ["customer", "staff"] else MessageSender.STAFF
    
    message = Message(
        conversation_id=conversation.id,
        content=data.content,
        sender_type=sender_type,
        sender_id=current_user["user_id"] if sender_type == MessageSender.STAFF else None,
    )
    db.add(message)
    
    # Update conversation timestamp
    conversation.last_message_at = datetime.utcnow()
    
    # If customer message and AI is enabled, generate AI response
    if sender_type == MessageSender.CUSTOMER and conversation.is_ai_enabled:
        # Get business info for AI context
        business = db.query(Business).filter(Business.id == current_user["business_id"]).first()
        
        # Get RAG context
        context = rag_service.get_context(data.content, str(current_user["business_id"]))
        
        # Get conversation history
        history = []
        for msg in conversation.messages[-10:]:
            history.append({
                "role": msg.sender_type.value,
                "content": msg.content
            })
        
        # Process through AI
        ai_result = await ai_service.process_message(
            message=data.content,
            persona=conversation.ai_persona or "general",
            business_name=business.name if business else "Business",
            business_type=business.business_type if business else "general",
            ai_tone=business.ai_tone if business else "professional",
            ai_language=business.ai_language if business else "en",
            conversation_history=history,
            context=context
        )
        
        # Save AI response as a message
        ai_message = Message(
            conversation_id=conversation.id,
            content=ai_result["response_text"],
            sender_type=MessageSender.AI,
            ai_intent=ai_result["intent"],
            ai_confidence=80,
            ai_action_taken=ai_result["action"],
        )
        db.add(ai_message)
        
        # Update conversation sentiment
        conversation.sentiment_score = ai_result["sentiment"]
        
        # Trigger automation workflows
        await automation_engine.evaluate_trigger(
            db=db,
            business_id=str(current_user["business_id"]),
            trigger_type="message_received",
            trigger_data={
                "message": data.content,
                "intent": ai_result["intent"],
                "sentiment": ai_result["sentiment"],
                "customer_id": str(conversation.customer_id),
                "conversation_id": str(conversation.id),
            }
        )
    
    db.commit()
    db.refresh(message)
    return message


@router.post("/{conversation_id}/takeover")
def human_takeover(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable AI and assign conversation to current human agent."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.business_id == current_user["business_id"]
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.is_ai_enabled = False
    conversation.assigned_to = current_user["user_id"]
    conversation.status = ConversationStatus.ACTIVE
    db.commit()
    
    return {"message": "Human takeover activated", "assigned_to": current_user["user_id"]}


@router.post("/{conversation_id}/enable-ai")
def enable_ai(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-enable AI for a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.business_id == current_user["business_id"]
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.is_ai_enabled = True
    conversation.status = ConversationStatus.AI_HANDLING
    db.commit()
    
    return {"message": "AI re-enabled for conversation"}
@router.post("/{conversation_id}/persona/{persona}")
def set_persona(
    conversation_id: UUID,
    persona: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the AI persona for a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.business_id == current_user["business_id"]
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    valid_personas = ["general", "sales", "support", "concierge"]
    if persona not in valid_personas:
        raise HTTPException(status_code=400, detail=f"Invalid persona. Must be one of: {valid_personas}")
        
    conversation.ai_persona = persona
    db.commit()
    
    return {"message": f"AI Persona updated to {persona}", "persona": persona}
