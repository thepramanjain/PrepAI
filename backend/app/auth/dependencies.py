"""
app/auth/dependencies.py

FastAPI dependency for verifying JWT tokens and extracting the current user.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.jwt import decode_access_token
from app.services.auth_service import get_user_by_id
from app.schemas.user import UserResponse

# This tells FastAPI where the token URL is (only for Swagger UI auto-complete)
# We use /api/auth/login since that's our login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Validate the token and return the user document from MongoDB.
    Raises 401 if invalid, expired, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception

    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
        
    return user


def get_current_user_response(user: dict = Depends(get_current_user)) -> UserResponse:
    """
    Helper dependency to automatically convert the MongoDB user dict 
    into a safe Pydantic UserResponse model.
    """
    return UserResponse(**user)
