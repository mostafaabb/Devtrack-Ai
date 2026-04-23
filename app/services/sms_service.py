"""
SMS Service - Twilio Integration for DevTrack AI
Send SMS and WhatsApp messages via Twilio
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS and WhatsApp messages via Twilio"""
    
    def __init__(self):
        from app.core.config import settings
        
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN  
        self.phone_number = settings.TWILIO_PHONE_NUMBER
        self.whatsapp_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)
        self.client = None
        
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio SMS service initialized")
            except ImportError:
                logger.warning("Twilio package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio: {e}")
    
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured"""
        return self.client is not None and self.phone_number is not None
    
    async def send_sms(
        self,
        to: str,
        message: str,
        from_number: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an SMS message
        
        Args:
            to: Recipient phone number (E.164 format, e.g., +1234567890)
            message: Message content (max 1600 characters for long SMS)
            from_number: Sender phone number (defaults to configured number)
            media_urls: List of media URLs for MMS
            callback_url: Webhook URL for status updates
            
        Returns:
            Dict with message SID, status, and details
        """
        if not self.is_configured():
            logger.warning("SMS service not configured - returning demo response")
            return {
                "success": True,
                "sid": f"demo_sms_{datetime.utcnow().timestamp()}",
                "status": "sent",
                "to": to,
                "demo_mode": True
            }
        
        try:
            # Format phone number
            to_formatted = self._format_phone_number(to)
            
            # Build message params
            params = {
                "to": to_formatted,
                "from_": from_number or self.phone_number,
                "body": message[:1600]  # Twilio limit
            }
            
            if media_urls:
                params["media_url"] = media_urls
                
            if callback_url:
                params["status_callback"] = callback_url
            
            # Send via Twilio
            msg = self.client.messages.create(**params)
            
            logger.info(f"SMS sent successfully: {msg.sid}")
            
            return {
                "success": True,
                "sid": msg.sid,
                "status": msg.status,
                "to": msg.to,
                "from": msg.from_,
                "date_created": str(msg.date_created),
                "segments": len(message) // 160 + 1
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": to
            }
    
    async def send_whatsapp(
        self,
        to: str,
        message: str,
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, str]] = None,
        media_url: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Twilio
        
        Args:
            to: Recipient phone number
            message: Message content (or template content)
            template_name: Pre-approved template name for business-initiated messages
            template_params: Parameters for template
            media_url: URL of media to send
            callback_url: Webhook URL for status updates
            
        Returns:
            Dict with message SID and status
        """
        if not self.is_configured():
            return {
                "success": True,
                "sid": f"demo_wa_{datetime.utcnow().timestamp()}",
                "status": "sent",
                "to": to,
                "demo_mode": True
            }
        
        try:
            # Format for WhatsApp
            to_formatted = self._format_phone_number(to)
            whatsapp_to = f"whatsapp:{to_formatted}"
            whatsapp_from = f"whatsapp:{self.whatsapp_number or self.phone_number}"
            
            params = {
                "to": whatsapp_to,
                "from_": whatsapp_from,
                "body": message
            }
            
            if media_url:
                params["media_url"] = [media_url]
                
            if callback_url:
                params["status_callback"] = callback_url
            
            msg = self.client.messages.create(**params)
            
            return {
                "success": True,
                "sid": msg.sid,
                "status": msg.status,
                "to": to,
                "channel": "whatsapp"
            }
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": to
            }
    
    async def send_bulk_sms(
        self,
        recipients: List[Dict[str, Any]],
        message_template: str,
        rate_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Send SMS to multiple recipients with personalization
        
        Args:
            recipients: List of dicts with 'phone' and optional personalization fields
            message_template: Message with {field} placeholders
            rate_limit: Messages per second (Twilio rate limit is ~10/sec)
            
        Returns:
            Dict with sent count, failed count, and details
        """
        import asyncio
        
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        for i, recipient in enumerate(recipients):
            phone = recipient.get("phone")
            if not phone:
                results["failed"] += 1
                results["details"].append({
                    "phone": None,
                    "error": "No phone number provided"
                })
                continue
            
            # Personalize message
            personalized_message = message_template
            for key, value in recipient.items():
                placeholder = "{" + key + "}"
                personalized_message = personalized_message.replace(placeholder, str(value or ""))
            
            # Send SMS
            result = await self.send_sms(phone, personalized_message)
            
            if result.get("success"):
                results["sent"] += 1
            else:
                results["failed"] += 1
                
            results["details"].append(result)
            
            # Rate limiting
            if (i + 1) % rate_limit == 0:
                await asyncio.sleep(1)
        
        return results
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get the status of a sent message"""
        if not self.is_configured():
            return {
                "sid": message_sid,
                "status": "delivered",
                "demo_mode": True
            }
        
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": message.to,
                "from": message.from_,
                "date_sent": str(message.date_sent),
                "date_updated": str(message.date_updated),
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
        except Exception as e:
            logger.error(f"Failed to get message status: {e}")
            return {
                "error": str(e),
                "sid": message_sid
            }
    
    async def verify_phone_number(
        self,
        phone: str,
        channel: str = "sms"
    ) -> Dict[str, Any]:
        """
        Start phone verification via Twilio Verify
        
        Args:
            phone: Phone number to verify
            channel: 'sms' or 'call'
            
        Returns:
            Dict with verification status
        """
        if not self.is_configured():
            return {
                "success": True,
                "status": "pending",
                "phone": phone,
                "demo_mode": True,
                "demo_code": "123456"
            }
        
        try:
            from app.core.config import settings
            verify_service_sid = getattr(settings, 'TWILIO_VERIFY_SERVICE_SID', None)
            
            if not verify_service_sid:
                return {
                    "success": False,
                    "error": "Verify service not configured"
                }
            
            verification = self.client.verify \
                .v2 \
                .services(verify_service_sid) \
                .verifications \
                .create(to=self._format_phone_number(phone), channel=channel)
            
            return {
                "success": True,
                "status": verification.status,
                "phone": phone,
                "channel": channel
            }
            
        except Exception as e:
            logger.error(f"Phone verification failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_verification_code(
        self,
        phone: str,
        code: str
    ) -> Dict[str, Any]:
        """
        Check a verification code
        
        Args:
            phone: Phone number being verified
            code: 6-digit verification code
            
        Returns:
            Dict with verification status
        """
        if not self.is_configured():
            # Demo mode - accept "123456" as valid
            is_valid = code == "123456"
            return {
                "success": is_valid,
                "status": "approved" if is_valid else "failed",
                "phone": phone,
                "demo_mode": True
            }
        
        try:
            from app.core.config import settings
            verify_service_sid = getattr(settings, 'TWILIO_VERIFY_SERVICE_SID', None)
            
            if not verify_service_sid:
                return {
                    "success": False,
                    "error": "Verify service not configured"
                }
            
            verification_check = self.client.verify \
                .v2 \
                .services(verify_service_sid) \
                .verification_checks \
                .create(to=self._format_phone_number(phone), code=code)
            
            return {
                "success": verification_check.status == "approved",
                "status": verification_check.status,
                "phone": phone
            }
            
        except Exception as e:
            logger.error(f"Verification check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number to E.164 format"""
        # Remove all non-numeric characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Ensure it starts with +
        if not cleaned.startswith('+'):
            # Assume US number if no country code
            if len(cleaned) == 10:
                cleaned = '+1' + cleaned
            elif len(cleaned) == 11 and cleaned.startswith('1'):
                cleaned = '+' + cleaned
            else:
                cleaned = '+' + cleaned
        
        return cleaned
    
    async def lookup_phone(self, phone: str) -> Dict[str, Any]:
        """
        Lookup phone number information via Twilio Lookup
        
        Returns carrier info, line type, caller name (if available)
        """
        if not self.is_configured():
            return {
                "phone": phone,
                "valid": True,
                "line_type": "mobile",
                "demo_mode": True
            }
        
        try:
            lookup = self.client.lookups \
                .v2 \
                .phone_numbers(self._format_phone_number(phone)) \
                .fetch()
            
            return {
                "phone": lookup.phone_number,
                "valid": lookup.valid,
                "country_code": lookup.country_code,
                "national_format": lookup.national_format,
                "carrier": getattr(lookup, 'carrier', None),
                "caller_name": getattr(lookup, 'caller_name', None)
            }
            
        except Exception as e:
            logger.error(f"Phone lookup failed: {e}")
            return {
                "phone": phone,
                "valid": False,
                "error": str(e)
            }


# Global instance
sms_service = SMSService()
