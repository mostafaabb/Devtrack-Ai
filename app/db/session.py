"""
Database session management.
Provides SQLAlchemy engine, session factory, and dependency injection for FastAPI.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings

# Create SQLAlchemy engine
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},  # Required for SQLite/FastAPI
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,        # Verify connections before use
        pool_size=20,               # Maximum pool size
        max_overflow=10,            # Allow 10 extra connections beyond pool_size
        pool_recycle=300,           # Recycle connections after 5 minutes
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    Automatically closes the session when the request is complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Called during application startup.
    """
    # Import ALL models to register them with SQLAlchemy
    from app.models import (
        User, Business, BusinessModule, Customer, Conversation, Message,
        Order, OrderItem, Booking, Product, Category, Service,
        Document, DocumentChunk, Workflow, AnalyticsEvent, ModuleDefinition,
        Notification, AuditLog, StaffInvitation,
    )
    Base.metadata.create_all(bind=engine)
