"""
WealthBot Security Module
=========================
Security utilities for authentication, encryption, and PII protection.
"""

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

# =============================================================================
# Password Hashing
# =============================================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Increased for better security
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT Token Management
# =============================================================================

class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str
    exp: datetime
    iat: datetime
    type: str = "access"


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The token subject (usually user ID).
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token string.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token with longer expiry.

    Args:
        subject: The token subject (usually user ID).
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT refresh token string.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> TokenPayload | None:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT token string.

    Returns:
        TokenPayload if valid and type is "access", None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        token_data = TokenPayload(**payload)
        if token_data.type != "access":
            return None
        return token_data
    except JWTError:
        return None


def decode_refresh_token(token: str) -> TokenPayload | None:
    """
    Decode and validate a JWT refresh token.

    Args:
        token: The JWT refresh token string.

    Returns:
        TokenPayload if valid and type is "refresh", None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        token_data = TokenPayload(**payload)
        if token_data.type != "refresh":
            return None
        return token_data
    except JWTError:
        return None


# =============================================================================
# PII Protection (GDPR/SOC 2 Compliance)
# =============================================================================

# Common PII patterns for masking
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
}


def mask_pii(data: str, pattern_type: str | None = None) -> str:
    """
    Mask PII in a string.

    Args:
        data: The string potentially containing PII
        pattern_type: Specific pattern to mask (optional)

    Returns:
        String with PII masked
    """
    if not settings.enable_pii_masking:
        return data

    masked_data = data
    patterns = (
        {pattern_type: PII_PATTERNS[pattern_type]}
        if pattern_type and pattern_type in PII_PATTERNS
        else PII_PATTERNS
    )

    for name, pattern in patterns.items():
        if name == "email":
            masked_data = pattern.sub("***@***.***", masked_data)
        elif name == "phone":
            masked_data = pattern.sub("***-***-****", masked_data)
        elif name == "ssn":
            masked_data = pattern.sub("***-**-****", masked_data)
        elif name == "credit_card":
            masked_data = pattern.sub("****-****-****-****", masked_data)

    return masked_data


def mask_email(email: str) -> str:
    """
    Partially mask an email address for display.

    Example: john.doe@example.com -> j***e@e***.com
    """
    if not email or "@" not in email:
        return email

    local, domain = email.rsplit("@", 1)

    masked_local = local[0] + "***" if len(local) <= 2 else local[0] + "***" + local[-1]

    domain_parts = domain.rsplit(".", 1)
    if len(domain_parts) == 2:
        masked_domain = domain_parts[0][0] + "***." + domain_parts[1]
    else:
        masked_domain = domain[0] + "***"

    return f"{masked_local}@{masked_domain}"


def hash_pii(value: str) -> str:
    """
    Create a one-way hash of PII for storage/comparison.

    Uses SHA-256 with the application's secret key as salt.
    """
    salted_value = f"{settings.secret_key}{value}"
    return hashlib.sha256(salted_value.encode()).hexdigest()


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize a dictionary for safe logging.

    Removes or masks sensitive fields.
    """
    sensitive_fields = {
        "password",
        "token",
        "secret",
        "api_key",
        "credit_card",
        "ssn",
        "social_security",
    }

    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_fields:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str):
            sanitized[key] = mask_pii(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized
