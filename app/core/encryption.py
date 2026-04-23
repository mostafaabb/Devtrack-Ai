"""
Encryption utilities for securing sensitive data at rest.
Uses Fernet symmetric encryption for API tokens, payment keys, etc.
"""
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
import base64
import hashlib
import logging

logger = logging.getLogger("devtrack.encryption")


def _get_fernet_key() -> bytes:
    """Derive a Fernet-compatible key from the app's SECRET_KEY."""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_value(value: str) -> str:
    """
    Encrypt a plain text value (API token, payment key, etc.).
    Returns a base64-encoded encrypted string.
    """
    if not value:
        return ""
    try:
        f = Fernet(_get_fernet_key())
        return f.encrypt(value.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError("Failed to encrypt value")


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted value back to plain text.
    Returns the original string.
    """
    if not encrypted_value:
        return ""
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(encrypted_value.encode()).decode()
    except InvalidToken:
        logger.error("Decryption failed: invalid token or corrupted data")
        return ""
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ""


def is_encrypted(value: str) -> bool:
    """Check if a value appears to be Fernet-encrypted."""
    if not value:
        return False
    try:
        f = Fernet(_get_fernet_key())
        f.decrypt(value.encode())
        return True
    except Exception:
        return False
