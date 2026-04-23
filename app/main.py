"""
DevTrack AI - Unified AI Business Operating System
Main FastAPI application entry point.

Production-ready with:
- Structured logging
- Redis-backed rate limiting
- Security headers & CSP
- WebSocket support
- Global error handling
- Database migrations
- Sentry error tracking
- Audit trail
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging

from app.core.config import settings
from app.core.logging import logger
from app.core.middleware import setup_middleware
from app.db.session import init_db

# Import all API routers
from app.api.auth import router as auth_router
from app.api.business import router as business_router
from app.api.conversations import router as conversations_router
from app.api.chat import router as chat_router
from app.api.websocket import router as ws_router
from app.api.routes import (
    customers_router,
    orders_router,
    bookings_router,
    products_router,
    categories_router,
    services_router,
    documents_router,
    workflows_router,
    analytics_router,
)

# Import new enterprise feature routers
from app.api.payments import router as payments_router
from app.api.inventory import router as inventory_router
from app.api.coupons import router as coupons_router
from app.api.loyalty import router as loyalty_router
from app.api.campaigns import router as campaigns_router
from app.api.team import router as team_router
from app.api.reports import router as reports_router

# ═══════════════════════════════════════════════════════════════════
# Initialize Sentry (Error Tracking)
# ═══════════════════════════════════════════════════════════════════

if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment="production" if not settings.DEBUG else "development",
        )
        logger.info("✅ Sentry error tracking initialized")
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed — error tracking disabled")

# ═══════════════════════════════════════════════════════════════════
# Create FastAPI Application
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified AI Business Operating System - Multi-industry SaaS platform",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# ═══════════════════════════════════════════════════════════════════
# Middleware Stack
# ═══════════════════════════════════════════════════════════════════

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Production middleware (logging, rate limiting, security headers, error handling)
setup_middleware(app, debug=settings.DEBUG)

# ═══════════════════════════════════════════════════════════════════
# Register API Routes
# ═══════════════════════════════════════════════════════════════════

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(business_router, prefix=API_PREFIX)
app.include_router(conversations_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(customers_router, prefix=API_PREFIX)
app.include_router(orders_router, prefix=API_PREFIX)
app.include_router(bookings_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)
app.include_router(categories_router, prefix=API_PREFIX)
app.include_router(services_router, prefix=API_PREFIX)
app.include_router(documents_router, prefix=API_PREFIX)
app.include_router(workflows_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)

# Enterprise feature routes
app.include_router(payments_router, prefix=API_PREFIX)
app.include_router(inventory_router, prefix=API_PREFIX)
app.include_router(coupons_router, prefix=API_PREFIX)
app.include_router(loyalty_router, prefix=API_PREFIX)
app.include_router(campaigns_router, prefix=API_PREFIX)
app.include_router(team_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)

# WhatsApp webhook routes (registered dynamically)
try:
    from app.api.whatsapp import router as whatsapp_router
    app.include_router(whatsapp_router, prefix=API_PREFIX)
except Exception:
    pass

# WebSocket routes (no prefix — ws:// protocol)
app.include_router(ws_router)

# ═══════════════════════════════════════════════════════════════════
# Static Files & Frontend
# ═══════════════════════════════════════════════════════════════════

# Serve the frontend dashboard
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

# Serve chat widget
widget_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "widget")
if os.path.exists(widget_dir):
    app.mount("/widget", StaticFiles(directory=widget_dir), name="widget")

# ═══════════════════════════════════════════════════════════════════
# Startup & Shutdown Events
# ═══════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"   Environment: {'DEVELOPMENT' if settings.DEBUG else 'PRODUCTION'}")

    # Initialize database tables
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization: {e}")
        logger.info("   Run 'alembic upgrade head' after starting PostgreSQL")

    # Create uploads directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Create logs directory
    os.makedirs("./logs", exist_ok=True)

    if settings.DEBUG:
        logger.info(f"📡 API Docs: http://localhost:8000/api/docs")
    logger.info(f"🌐 Dashboard: http://localhost:8000")
    logger.info(f"🔌 WebSocket: ws://localhost:8000/ws?token=<JWT>")
    logger.info(f"📧 Email: {'SMTP configured' if settings.SMTP_HOST else 'Dev mode (logging only)'}")
    logger.info(f"🔐 Email verification: {'Required' if settings.REQUIRE_EMAIL_VERIFICATION else 'Disabled'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    from app.core.websocket import ws_manager
    stats = ws_manager.get_stats()
    logger.info(
        f"👋 Shutting down {settings.APP_NAME} "
        f"(closing {stats['total_connections']} WebSocket connections)"
    )


# ═══════════════════════════════════════════════════════════════════
# Root & Health Routes
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Serve the frontend dashboard."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/api/docs",
    }


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Returns the app status, version, and service connectivity.
    """
    from app.core.websocket import ws_manager
    from sqlalchemy import text

    health = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "websocket": ws_manager.get_stats(),
    }

    # Check database connectivity
    try:
        from app.db.session import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health["database"] = "connected"
    except Exception:
        health["database"] = "disconnected"
        health["status"] = "degraded"

    # Check Redis connectivity
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health["redis"] = "connected"
    except Exception:
        health["redis"] = "disconnected"

    return health
