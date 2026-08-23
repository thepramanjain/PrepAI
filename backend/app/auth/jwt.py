"""
app/auth/jwt.py

JWT creation and decoding utility using PyJWT.
"""

import jwt
from datetime import datetime, timedelta, timezone

from app.config.settings import settings


def create_access_token(user_id: str) -> str:
    """
    Create a JWT access token for a user.
    Includes the 'sub' (subject) claim as the user's ID.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode a JWT token.
    Returns the payload if valid, raises jwt.PyJWTError if invalid or expired.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )
