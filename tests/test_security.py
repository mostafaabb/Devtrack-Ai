"""
Unit tests for DevTrack AI platform.
Run with: python -m pytest tests/
"""
import pytest
from app.core.security import hash_password, verify_password, validate_password_strength


class TestPasswordSecurity:
    """Test password hashing and validation."""

    def test_password_hashing(self):
        """Test that passwords can be hashed and verified."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_password_strength_validation(self):
        """Test password strength requirements."""
        # Valid password
        result = validate_password_strength("StrongPass123!")
        assert result["valid"]
        assert len(result["errors"]) == 0

        # Invalid passwords
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoDigits!",  # No digits
            "NoSpecial123",  # No special characters
        ]

        for password in weak_passwords:
            result = validate_password_strength(password)
            assert not result["valid"]
            assert len(result["errors"]) > 0

    def test_long_password(self):
        """Test that very long passwords work (bcrypt limit handling)."""
        long_password = "A" * 100  # 100 character password
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed)