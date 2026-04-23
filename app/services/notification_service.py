"""
Notification Service - Real-time alerts and cross-channel messaging.
Handles In-App (WebSocket), WhatsApp (per-business tokens), and Email notifications.
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from app.core.config import settings
from app.core.websocket import ws_manager
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.db.session import SessionLocal

logger = logging.getLogger("devtrack.notifications")

class NotificationService:
    """
    Central system for dispatching business notifications.
    
    1. In-App: Sends via WebSocket to active staff sessions
    2. WhatsApp: Sends via Meta Business API with per-business tokens
    3. Email: Sends via SMTP service
    4. Push: (Mobile ready via WebSocket)
    """

    async def send_in_app(
        self,
        business_id: str,
        title: str,
        message: str,
        type: str = "info",
        entity_type: str = None,
        entity_id: str = None,
        recipient_id: str = None,
    ):
        """
        Send a real-time notification to staff members in a business.
        """
        db = SessionLocal()
        try:
            notification = Notification(
                business_id=business_id,
                user_id=recipient_id,
                title=title,
                message=message,
                type=NotificationType(type),
                entity_type=entity_type,
                entity_id=entity_id,
                is_read=False,
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)

            # Dispatch via WebSocket
            ws_payload = {
                "type": "notification",
                "id": str(notification.id),
                "title": title,
                "message": message,
                "notification_type": type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if recipient_id:
                await ws_manager.send_to_user(business_id, recipient_id, ws_payload)
            else:
                await ws_manager.broadcast_to_business(business_id, ws_payload)
                
            return notification
        except Exception as e:
            logger.error(f"Failed to send in-app notification: {e}")
            return None
        finally:
            db.close()

    async def send_whatsapp(
        self,
        phone: str,
        template_name: str = None,
        message_text: str = None,
        language_code: str = "en",
        components: List[Dict] = None,
        business_api_token: str = None,
        business_phone_id: str = None,
    ):
        """
        Send a WhatsApp message via Meta Business API.
        Uses per-business tokens (priority) or falls back to global settings.
        
        Supports:
        - Template messages (for > 24h since last customer message)
        - Free-form text messages (within 24h window)
        """
        # Use per-business tokens if provided, otherwise fall back to global
        api_token = business_api_token or settings.WHATSAPP_API_TOKEN
        phone_id = business_phone_id or settings.WHATSAPP_PHONE_NUMBER_ID

        if not api_token:
            logger.warning("🚫 WhatsApp skipped: No API token configured.")
            return False

        if not phone_id:
            logger.warning("🚫 WhatsApp skipped: No Phone Number ID configured.")
            return False

        # Decrypt token if encrypted
        try:
            from app.core.encryption import decrypt_value, is_encrypted
            if is_encrypted(api_token):
                api_token = decrypt_value(api_token)
        except Exception:
            pass  # Use as-is if decryption fails

        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        # Build payload based on message type
        if message_text and not template_name:
            # Free-form text message (within 24h customer service window)
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone,
                "type": "text",
                "text": {"preview_url": False, "body": message_text}
            }
        else:
            # Template message
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name or "hello_world",
                    "language": {"code": language_code},
                    "components": components or []
                }
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"✅ WhatsApp sent to {phone}")
                    return True
                else:
                    logger.error(f"❌ WhatsApp API error ({response.status_code}): {response.text}")
                    return False
            except httpx.TimeoutException:
                logger.error(f"❌ WhatsApp request timeout for {phone}")
                return False
            except Exception as e:
                logger.error(f"❌ WhatsApp connection failed: {e}")
                return False

    async def send_order_status_update(
        self,
        business_id: str,
        order_number: str,
        new_status: str,
        customer_phone: str = None,
        customer_email: str = None,
        customer_name: str = "Customer",
        business_name: str = "Business",
        business_api_token: str = None,
        business_phone_id: str = None,
    ):
        """
        Send order status update via multiple channels.
        """
        # 1. In-app notification to staff
        await self.send_in_app(
            business_id=business_id,
            title=f"Order #{order_number} -> {new_status}",
            message=f"Order status updated to {new_status}",
            type="info",
            entity_type="order",
        )

        # 2. WhatsApp notification to customer
        if customer_phone and business_api_token:
            status_messages = {
                "confirmed": f"✅ Great news! Your order #{order_number} has been confirmed.",
                "preparing": f"👨‍🍳 Your order #{order_number} is being prepared!",
                "ready": f"📦 Your order #{order_number} is ready for pickup/delivery!",
                "out_for_delivery": f"🚚 Your order #{order_number} is on its way!",
                "delivered": f"🎉 Your order #{order_number} has been delivered. Enjoy!",
                "completed": f"✅ Your order #{order_number} is complete. Thank you!",
                "cancelled": f"❌ Your order #{order_number} has been cancelled.",
            }
            msg = status_messages.get(new_status, f"Your order #{order_number} status: {new_status}")
            await self.send_whatsapp(
                phone=customer_phone,
                message_text=msg,
                business_api_token=business_api_token,
                business_phone_id=business_phone_id,
            )

        # 3. Email notification to customer
        if customer_email:
            try:
                from app.core.email import email_service
                email_service.send_status_update(
                    to=customer_email,
                    customer_name=customer_name,
                    entity_type="order",
                    entity_number=order_number,
                    new_status=new_status,
                    business_name=business_name,
                )
            except Exception as e:
                logger.warning(f"Failed to send email status update: {e}")

    async def send_booking_status_update(
        self,
        business_id: str,
        booking_number: str,
        new_status: str,
        customer_phone: str = None,
        customer_email: str = None,
        customer_name: str = "Customer",
        business_name: str = "Business",
        business_api_token: str = None,
        business_phone_id: str = None,
    ):
        """
        Send booking status update via multiple channels.
        """
        await self.send_in_app(
            business_id=business_id,
            title=f"Booking #{booking_number} -> {new_status}",
            message=f"Booking status updated to {new_status}",
            type="info",
            entity_type="booking",
        )

        if customer_phone and business_api_token:
            status_messages = {
                "confirmed": f"✅ Your booking #{booking_number} is confirmed!",
                "cancelled": f"❌ Your booking #{booking_number} has been cancelled.",
                "completed": f"✅ Your booking #{booking_number} is complete. Thank you!",
                "no_show": f"We noticed you missed your booking #{booking_number}.",
            }
            msg = status_messages.get(new_status, f"Your booking #{booking_number} status: {new_status}")
            await self.send_whatsapp(
                phone=customer_phone,
                message_text=msg,
                business_api_token=business_api_token,
                business_phone_id=business_phone_id,
            )

        if customer_email:
            try:
                from app.core.email import email_service
                email_service.send_status_update(
                    to=customer_email,
                    customer_name=customer_name,
                    entity_type="booking",
                    entity_number=booking_number,
                    new_status=new_status,
                    business_name=business_name,
                )
            except Exception as e:
                logger.warning(f"Failed to send booking email: {e}")


# Global instance
notification_service = NotificationService()
