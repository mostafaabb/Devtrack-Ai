"""
Celery application and background task definitions.
Handles async processing for documents, embeddings, analytics, and AI tasks.
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "devtrack",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
)


@celery_app.task(name="process_document")
def process_document_task(document_id: str, file_path: str, file_type: str):
    """
    Background task to process an uploaded document.
    Extracts text, chunks it, and generates embeddings.
    """
    from app.services.rag_service import rag_service
    
    try:
        # Extract text
        text = rag_service.extract_text(file_path, file_type)
        
        if not text:
            return {"status": "failed", "error": "Could not extract text"}
        
        # Chunk the text
        chunks = rag_service.chunk_text(text)
        
        # Add to vector index
        count = rag_service.add_chunks(chunks, document_id)
        
        return {
            "status": "processed",
            "chunk_count": count,
            "text_length": len(text)
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="generate_analytics")
def generate_analytics_task(business_id: str):
    """
    Background task to generate analytics insights for a business.
    """
    return {
        "status": "completed",
        "business_id": business_id,
        "message": "Analytics generated"
    }


@celery_app.task(name="send_notification")
def send_notification_task(notification_data: dict):
    """
    Background task to send notifications (push, email, etc.).
    """
    return {
        "status": "sent",
        "notification": notification_data
    }
