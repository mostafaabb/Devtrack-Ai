"""
AI Service - Google Gemini Integration.
Handles the core AI conversation engine, intent detection, and decision layer.
"""
import json
from typing import Optional, Dict, Any, List
from app.core.config import settings

# Try to import Google Generative AI; if not available use mock mode
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AIService:
    """
    Core AI service using Google Gemini.
    
    Capabilities:
    - Context-aware conversation
    - Multilingual (Arabic, English, Lebanese dialect)
    - Intent detection (question, order, booking, complaint)
    - Sentiment analysis
    - Decision making (respond, create_order, create_booking, escalate)
    """

    def __init__(self):
        self.model = None
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')

    def _get_system_prompt(self, business_type: str, ai_tone: str, business_name: str, ai_language: str, persona: str = "general") -> str:
        """Build the system prompt based on business configuration and persona."""
        
        persona_instructions = {
            "general": "Be helpful, professional, and culturally aware.",
            "sales": "Focus on driving revenue. Suggest additions, upsell products, and be enthusiastic about the brand.",
            "support": "Handle complaints with extreme empathy. Focus on resolution and customer retention.",
            "concierge": "An expert in the business's knowledge base. Provide detailed, accurate information from the context."
        }
        
        instruction = persona_instructions.get(persona, persona_instructions["general"])

        return f"""You are an AI assistant for "{business_name}", a {business_type} business in Lebanon.
Persona: {persona}
Role: {instruction}

COMMUNICATION RULES:
- Respond in {ai_language} (support Arabic, English, and Lebanese dialect)
- Tone: {ai_tone}
- Represet the business directly

DECISION LAYER - Before responding, you MUST:
1. Detect the customer's INTENT:
   - "question" - asking for information
   - "order" - wanting to place an order
   - "booking" - wanting to make a reservation/appointment
   - "complaint" - expressing dissatisfaction
   - "payment" - asking about payment or wanting to pay
   - "greeting" - saying hello
   - "marketing_interest" - interested in a promotion
   - "other" - anything else

2. Analyze SENTIMENT:
   - Score from -100 (very negative) to 100 (very positive)

3. Decide ACTION:
   - "respond" - provide information or answer
   - "create_order" - customer wants to order, extract items
   - "create_booking" - customer wants to book, extract details
   - "generate_payment" - customer is ready to pay for an order
   - "escalate" - complex issue needs human attention
   - "visual_search" - customer sent an image (only if image data is provided)

RESPONSE FORMAT (JSON):
{{
    "response_text": "Your response to the customer",
    "intent": "question|order|booking|complaint|payment|greeting|marketing_interest|other",
    "sentiment": <score from -100 to 100>,
    "action": "respond|create_order|create_booking|generate_payment|escalate|visual_search",
    "action_data": {{}},
    "suggested_persona": "sales|support|concierge|general" // Decide if another persona should take over for the next message
}}

If action is "create_order":
action_data = {{"items": [{{"name": "...", "quantity": 1, "notes": "..."}}]}}

If action is "create_booking":
action_data = {{"date": "...", "time": "...", "party_size": 1, "service": "..."}}

If action is "generate_payment":
action_data = {{"order_id": "...", "amount": 0.0}}

If action is "visual_search":
action_data = {{"description_of_image": "...", "product_match_query": "..."}}

Always respond in valid JSON format."""

    async def process_message(
        self,
        message: str,
        persona: str = "general",
        business_name: str = "Business",
        business_type: str = "general",
        ai_tone: str = "professional",
        ai_language: str = "en",
        conversation_history: List[Dict[str, str]] = None,
        context: str = None
    ) -> Dict[str, Any]:
        """
        Process an incoming customer message through the AI decision layer.
        
        Args:
            message: Customer's message
            business_name: Name of the business
            business_type: Type of business (restaurant, hotel, etc.)
            ai_tone: Communication tone (professional, friendly, formal)
            ai_language: Language preference (en, ar, mixed)
            conversation_history: Previous messages for context
            context: RAG context from knowledge base
            
        Returns:
            Dict with response_text, intent, sentiment, action, action_data
        """
        system_prompt = self._get_system_prompt(business_type, ai_tone, business_name, ai_language, persona)
        
        # Build conversation context
        full_prompt = system_prompt + "\n\n"
        
        if context:
            full_prompt += f"RELEVANT KNOWLEDGE BASE CONTEXT:\n{context}\n\n"
        
        if conversation_history:
            full_prompt += "CONVERSATION HISTORY:\n"
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                role = msg.get("role", "customer")
                content = msg.get("content", "")
                full_prompt += f"{role}: {content}\n"
            full_prompt += "\n"
        
        full_prompt += f"CUSTOMER MESSAGE: {message}\n\nRespond in JSON format:"
        
        # If Gemini is available, use it
        if self.model:
            try:
                response = self.model.generate_content(full_prompt)
                result = self._parse_ai_response(response.text)
                return result
            except Exception as e:
                print(f"Gemini API error: {e}")
                return self._fallback_response(message)
        
        # Fallback mock response for development
        return self._fallback_response(message)

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response JSON."""
        try:
            # Try to extract JSON from the response
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            result = json.loads(text.strip())
            return {
                "response_text": result.get("response_text", "I'll help you with that."),
                "intent": result.get("intent", "other"),
                "sentiment": result.get("sentiment", 0),
                "action": result.get("action", "respond"),
                "action_data": result.get("action_data", {})
            }
        except (json.JSONDecodeError, Exception):
            return {
                "response_text": response_text,
                "intent": "other",
                "sentiment": 0,
                "action": "respond",
                "action_data": {}
            }

    def _fallback_response(self, message: str) -> Dict[str, Any]:
        """
        Provide intelligent fallback responses when Gemini is not available.
        Uses keyword matching for basic intent detection.
        """
        message_lower = message.lower()
        
        # Intent detection via keywords
        if any(w in message_lower for w in ["order", "buy", "اطلب", "بدي"]):
            intent = "order"
            action = "create_order"
            response = "I'd be happy to help you place an order! Could you tell me what you'd like to order?"
        elif any(w in message_lower for w in ["book", "reserve", "appointment", "حجز", "موعد"]):
            intent = "booking"
            action = "create_booking"
            response = "I'd love to help you make a booking! When would you like to schedule it?"
        elif any(w in message_lower for w in ["complaint", "problem", "issue", "bad", "شكوى", "مشكلة"]):
            intent = "complaint"
            action = "escalate"
            response = "I'm sorry to hear about your concern. Let me connect you with our team to resolve this."
        elif any(w in message_lower for w in ["hi", "hello", "hey", "مرحبا", "هلا", "كيفك"]):
            intent = "greeting"
            action = "respond"
            response = "Hello! Welcome! How can I help you today? 😊"
        else:
            intent = "question"
            action = "respond"
            response = "Thank you for your message! I'm here to help. Could you provide more details about what you need?"
        
        # Basic sentiment scoring
        positive_words = ["good", "great", "love", "excellent", "thanks", "حلو", "ممتاز"]
        negative_words = ["bad", "terrible", "hate", "worst", "سيء", "مشكلة"]
        
        sentiment = 0
        for w in positive_words:
            if w in message_lower:
                sentiment += 20
        for w in negative_words:
            if w in message_lower:
                sentiment -= 20
        
        sentiment = max(-100, min(100, sentiment))
        
        return {
            "response_text": response,
            "intent": intent,
            "sentiment": sentiment,
            "action": action,
            "action_data": {}
        }

    async def generate_insights(self, data: Dict[str, Any]) -> str:
        """
        Generate AI business insights from analytics data.
        
        Args:
            data: Business metrics data
            
        Returns:
            AI-generated insights text
        """
        if self.model:
            try:
                prompt = f"""As a business analyst, analyze this data and provide actionable insights:

{json.dumps(data, indent=2)}

Provide:
1. Key trends
2. Performance summary
3. Recommendations
4. Peak hours/patterns (if applicable)

Keep the response concise and actionable."""
                response = self.model.generate_content(prompt)
                return response.text
            except Exception:
                pass
        
        # Fallback insights
        return self._generate_fallback_insights(data)

    def _generate_fallback_insights(self, data: Dict[str, Any]) -> str:
        """Generate basic insights without AI."""
        total_orders = data.get("total_orders", 0)
        total_revenue = data.get("total_revenue", 0)
        total_customers = data.get("total_customers", 0)
        
        insights = []
        insights.append(f"📊 Business Performance Summary")
        insights.append(f"• Total Customers: {total_customers}")
        insights.append(f"• Total Orders: {total_orders}")
        insights.append(f"• Total Revenue: ${total_revenue:,.2f}")
        
        if total_orders > 0 and total_revenue > 0:
            avg_order = total_revenue / total_orders
            insights.append(f"• Average Order Value: ${avg_order:,.2f}")
        
        insights.append(f"\n💡 Recommendations:")
        insights.append(f"• Focus on customer engagement to increase repeat orders")
        insights.append(f"• Consider promotional campaigns during slower periods")
        
        return "\n".join(insights)


# Global AI service instance
ai_service = AIService()
