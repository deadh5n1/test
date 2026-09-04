"""
Security utilities: password hashing and session management.
"""
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from typing import Optional
from datetime import timedelta

from app.config import SECRET_KEY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_session_token(user_id: int) -> str:
    """Create a session token for a user."""
    return serializer.dumps(user_id)


def verify_session_token(token: str, max_age: int = 86400) -> Optional[int]:
    """Verify a session token and return the user ID."""
    try:
        user_id = serializer.loads(token, max_age=max_age)
        return user_id
    except (BadSignature, SignatureExpired):
        return None
