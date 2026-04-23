"""
WhatsApp Webhook API - Handles incoming messages from the Meta Business API.
Processes messages through the AI decision layer and triggers automation.
"""
from fastapi import APIRouter, Request, Response, Query, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import logging
from datetime import datetime

from app.core.config import settings
from app.db.session import get_db
from app.services.ai_service import ai_service
from app.services.rag_service import rag_service
from app.services.notification_service import notification_service
from app.models.conversation import Conversation, Message, MessageSender
from app.models.customer import Customer
from app.models.business import Business
from app.core.websocket import ws_manager

logger = logging.getLogger("devtrack.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

@router.get("/webhook/{business_id}")
def verify_webhook(
    business_id: str,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    db: Session = Depends(get_db)
):
    """
    Verification endpoint for Meta WhatsApp Webhook setup.
    Matches the specific verify_token stored in the Business record.
    """
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        logger.warning(f"❌ Webhook verification failed: Business {business_id} not found.")
        raise HTTPException(status_code=404, detail="Business not found")

    # Use the business-specific token, or fallback to global for backwards compatibility during migration
    expected_token = business.whatsapp_verify_token or settings.WHATSAPP_VERIFY_TOKEN
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info(f"✅ WhatsApp Webhook Verified for Business: {business.name}")
        return Response(content=hub_challenge)
    
    logger.warning(f"❌ WhatsApp Webhook Verification Failed for Business: {business.name}")
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook/{business_id}")
async def handle_whatsapp_message(
    business_id: str, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    Processes incoming WhatsApp messages.
    
    1. Extract message, phone, and sender
    2. Identify/Create customer and business context
    3. Run through AI + RAG knowledge base
    4. Auto-reply via WhatsApp
    5. Broadcast to dashboard via WebSocket
    """
    payload = await request.json()
    logger.debug(f"Incoming WhatsApp Payload: {json.dumps(payload)}")

    # 1. Extract message details from Meta payload structure
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            return {"status": "ignored"}
            
        message = messages[0]
        from_phone = message.get("from")
        message_text = message.get("text", {}).get("body", "")
        wa_id = message.get("id")
        
        # 2. Get business context from the URL
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            logger.error(f"❌ Received WhatsApp message for non-existent business: {business_id}")
            return {"status": "no_business"}

        # 3. Handle Customer CRM
        customer = db.query(Customer).filter(Customer.phone == from_phone).first()
        if not customer:
            customer = Customer(
                business_id=business.id,
                name=f"WA User {from_phone[-4:]}",
                phone=from_phone,
                channel="whatsapp"
            )
            db.add(customer)
            db.flush()

        # 4. Handle Conversation Thread
        conv = db.query(Conversation).filter(
            Conversation.customer_id == customer.id,
            Conversation.status != "archived"
        ).first()
        
        if not conv:
            conv = Conversation(
                business_id=business.id,
                customer_id=customer.id,
                status="ai_handling",
                last_message_at=datetime.utcnow()
            )
            db.add(conv)
            db.flush()

        # 5. Save incoming message
        db_msg = Message(
            conversation_id=conv.id,
            sender=MessageSender.CUSTOMER,
            content=message_text,
            status="delivered",
            whatsapp_message_id=wa_id
        )
        db.add(db_msg)
        db.commit()

        # 6. Broadcast to Dashboard UI for real-time view
        await ws_manager.broadcast_to_business(str(business.id), {
            "type": "message",
            "conversation_id": str(conv.id),
            "sender": "customer",
            "content": message_text,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 7. AI Processing + RAG
        context = rag_service.get_context(message_text, str(business.id))
        ai_response = await ai_service.process_message(
            message=message_text,
            persona=conv.ai_persona or "general",
            business_name=business.name,
            business_type=business.business_type,
            context=context
        )

        response_text = ai_response.get("response_text", "I'll get back to you shortly.")

        # 8. Send WhatsApp Reply back to customer using business-specific tokens
        await notification_service.send_whatsapp(
            phone=from_phone,
            message_text=response_text,
            business_api_token=business.whatsapp_api_token,
            business_phone_id=business.whatsapp_phone_number_id,
        )

        # 9. Save AI Response
        ai_msg = Message(
            conversation_id=conv.id,
            sender=MessageSender.AI,
            content=response_text,
            status="sent"
        )
        db.add(ai_msg)
        db.commit()

        # 10. Broadcast AI Response to Dashboard
        await ws_manager.broadcast_to_business(str(business.id), {
            "type": "message",
            "conversation_id": str(conv.id),
            "sender": "ai",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
            "intent": ai_response.get("intent")
        })

        return {"status": "success"}

    except Exception as e:
        logger.error(f"❌ WhatsApp handling error: {e}")
        return {"status": "error", "detail": str(e)}
