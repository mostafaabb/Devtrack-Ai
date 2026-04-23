"""
Celery Background Tasks - Handling long-running business operations.
- AI Business Analytics Insight Generation
- Document Processing (OCR/Text Extraction)
- Scheduled Notifications (Reminders)
- Automation Workflow Execution
"""
from celery import Celery
from datetime import datetime
import logging
from typing import Dict, Any

from app.core.config import settings
from app.services.ai_service import ai_service
from app.services.notification_service import notification_service
from app.services.rag_service import rag_service
from app.db.session import SessionLocal
from app.models.analytics import AnalyticsEvent

logger = logging.getLogger("devtrack.workers")

# 1. Initialize Celery
celery_app = Celery(
    "devtrack_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# 2. Configuration for scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    'daily-business-insights': {
        'task': 'app.workers.tasks.generate_daily_insights',
        'schedule': 86400.0, # Every 24 hours
    },
    'cleanup-old-logs': {
        'task': 'app.workers.tasks.cleanup_logs',
        'schedule': 604800.0, # Every week
    }
}

# 3. Task: Generate AI Analytics Insight
@celery_app.task(name="app.workers.tasks.generate_daily_insights")
def generate_insights_task(business_id: str, data: Dict[str, Any]):
    """
    Backround task to generate AI insights from business data.
    """
    try:
        # 1. Call AI service for analysis
        # (This is an async function in AI service, so we use it accordingly)
        # For simplicity in Celery, we sync-wrap it
        import asyncio
        insights = asyncio.run(ai_service.generate_insights(data))
        
        # 2. Store or Notify
        # (Save insights to the DB or send to the dashboard via WS)
        return {"status": "success", "insights": insights}
    except Exception as e:
        logger.error(f"Insight task failed: {e}")
        return {"status": "error", "message": str(e)}

# 4. Task: Process Uploaded Document
@celery_app.task(name="app.workers.tasks.process_document")
def process_document_task(document_id: str, file_path: str, file_type: str):
    """
    Handles PDF/TXT extraction and FAISS vector embedding in the background.
    """
    try:
        # 1. Extract text
        text = rag_service.extract_text(file_path, file_type)
        if not text:
            return {"status": "empty"}
            
        # 2. Chunk and Embed
        chunks = rag_service.chunk_text(text)
        rag_service.add_chunks(chunks, document_id)
        
        # 3. Update Document DB Status
        # We use a fresh session in the worker
        db = SessionLocal()
        from app.models.document import Document
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "processed"
            doc.processed_at = datetime.utcnow()
            doc.chunk_count = len(chunks)
            db.commit()
        db.close()
        
        return {"status": "success", "chunk_count": len(chunks)}
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        return {"status": "error", "message": str(e)}

# 5. Task: Send Scheduled Reminder
@celery_app.task(name="app.workers.tasks.send_reminder")
def send_reminder_task(phone: str, message: str):
    """
    Background task to send a delayed notification (e.g., booking reminder).
    """
    import asyncio
    asyncio.run(notification_service.send_whatsapp(phone, "reminder_template", components=[
        { "type": "body", "parameters": [{ "type": "text", "text": message }] }
    ]))
    return {"status": "sent"}
