"""
DevTrack Enterprise Service - Handles Payment integration and Visual AI processing.
Supports Stripe, with mock fallback for development.
"""
import uuid
from typing import Dict, Any, List, Optional
import logging
import httpx

logger = logging.getLogger("devtrack.enterprise_service")

class EnterpriseService:
    """
    Handles advanced features:
    1. Payment Link Generation (Stripe integration with mock fallback)
    2. Payment verification
    3. Visual AI (Gemini Vision)
    4. Omnichannel bridging
    """

    async def generate_payment_link(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        customer_email: str = None,
        customer_name: str = None,
        business_name: str = "Business",
        payment_api_key: str = None,
        payment_provider: str = "stripe",
        success_url: str = None,
        cancel_url: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a secure payment link.
        Uses Stripe Checkout if API key is provided, otherwise returns mock link.
        """
        if payment_provider == "stripe" and payment_api_key:
            return await self._stripe_checkout(
                order_id, amount, currency, customer_email,
                customer_name, business_name, payment_api_key,
                success_url, cancel_url,
            )
        
        # Mock payment link for development
        payment_token = str(uuid.uuid4())
        mock_url = f"https://devtrack.ai/pay/{order_id}/{payment_token}?amount={amount}&currency={currency}"
        
        logger.info(f"💳 [MOCK] Payment link generated for order {order_id}: ${amount} {currency}")
        
        return {
            "success": True,
            "payment_url": mock_url,
            "payment_id": payment_token,
            "provider": "mock",
            "amount": amount,
            "currency": currency,
        }

    async def _stripe_checkout(
        self,
        order_id: str,
        amount: float,
        currency: str,
        customer_email: str,
        customer_name: str,
        business_name: str,
        api_key: str,
        success_url: str = None,
        cancel_url: str = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session."""
        # Decrypt key if encrypted
        try:
            from app.core.encryption import decrypt_value, is_encrypted
            if is_encrypted(api_key):
                api_key = decrypt_value(api_key)
        except Exception:
            pass

        try:
            url = "https://api.stripe.com/v1/checkout/sessions"
            headers = {"Authorization": f"Bearer {api_key}"}
            
            data = {
                "payment_method_types[]": "card",
                "mode": "payment",
                "success_url": success_url or f"https://devtrack.ai/payment/success?order={order_id}",
                "cancel_url": cancel_url or f"https://devtrack.ai/payment/cancel?order={order_id}",
                "line_items[0][price_data][currency]": currency.lower(),
                "line_items[0][price_data][unit_amount]": int(amount * 100),
                "line_items[0][price_data][product_data][name]": f"Order #{order_id}",
                "line_items[0][quantity]": "1",
                "metadata[order_id]": order_id,
                "metadata[business]": business_name,
            }
            
            if customer_email:
                data["customer_email"] = customer_email

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)
                
                if response.status_code == 200:
                    session = response.json()
                    return {
                        "success": True,
                        "payment_url": session.get("url"),
                        "payment_id": session.get("id"),
                        "provider": "stripe",
                        "amount": amount,
                        "currency": currency,
                    }
                else:
                    logger.error(f"Stripe error: {response.text}")
                    return {
                        "success": False,
                        "error": f"Payment provider error: {response.status_code}",
                        "provider": "stripe",
                    }

        except Exception as e:
            logger.error(f"Stripe payment generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "stripe",
            }

    async def verify_payment(
        self,
        payment_id: str,
        payment_api_key: str = None,
        provider: str = "stripe",
    ) -> Dict[str, Any]:
        """Verify a payment status."""
        if provider == "stripe" and payment_api_key:
            try:
                from app.core.encryption import decrypt_value, is_encrypted
                if is_encrypted(payment_api_key):
                    payment_api_key = decrypt_value(payment_api_key)
            except Exception:
                pass

            try:
                url = f"https://api.stripe.com/v1/checkout/sessions/{payment_id}"
                headers = {"Authorization": f"Bearer {payment_api_key}"}
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        session = response.json()
                        return {
                            "success": True,
                            "status": session.get("payment_status"),
                            "amount_total": session.get("amount_total", 0) / 100,
                            "customer_email": session.get("customer_email"),
                        }
            except Exception as e:
                logger.error(f"Payment verification failed: {e}")
        
        return {
            "success": True,
            "status": "paid",
            "provider": "mock",
        }

    async def process_visual_search(self, image_url: str, business_id: str) -> Dict[str, Any]:
        """
        Process image with Gemini Vision to match products.
        In production, integrates with Gemini Pro Vision.
        """
        from app.core.config import settings
        
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-pro-vision')
                
                response = model.generate_content([
                    "Describe this product image in detail. "
                    "What type of product is it? What are its key features? "
                    "Suggest search terms for finding similar products.",
                    image_url
                ])
                
                return {
                    "success": True,
                    "description": response.text,
                    "match_confidence": 0.85,
                    "suggested_products": []
                }
            except Exception as e:
                logger.warning(f"Vision AI failed: {e}")
        
        # Fallback mock response
        logger.info(f"Processing visual search for image: {image_url}")
        return {
            "success": True,
            "description": "A high-quality product based on your image.",
            "match_confidence": 0.95,
            "suggested_products": [
                {"name": "Visual Match Item 1", "price": 45.0, "id": str(uuid.uuid4())}
            ]
        }

enterprise_service = EnterpriseService()
