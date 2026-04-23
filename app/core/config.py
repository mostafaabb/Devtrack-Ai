"""
Core configuration module for DevTrack AI platform.
Loads settings from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "DevTrack AI"
    APP_VERSION: str = "2.0.0"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "postgresql://devtrack:devtrack123@localhost:5432/devtrack"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Google Gemini AI
    GEMINI_API_KEY: str = ""

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    JWT_REFRESH_EXPIRATION_DAYS: int = 30

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://localhost:5173,http://localhost:8000"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # WhatsApp Integration
    WHATSAPP_API_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    META_APP_ID: str = ""

    # SMTP Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@devtrack.ai"
    SMTP_USE_TLS: bool = True

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./uploads"

    # Security
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 8
    REQUIRE_EMAIL_VERIFICATION: bool = False  # Set True in production

    # Sentry Error Tracking
    SENTRY_DSN: str = ""

    # Stripe Payments
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Twilio SMS
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # API URL (for tracking links, webhooks)
    API_URL: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

# Global settings instance
settings = Settings()
