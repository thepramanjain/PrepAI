"""
app/services/auth_service.py

Business logic for authentication: Registration, Login, User retrieval.
"""

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from app.models.user import users_collection
from app.schemas.auth import RegisterRequest, LoginRequest
from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.utils.helpers import utc_now


def register_user(data: RegisterRequest) -> dict:
    """Register a new user."""
    
    # Normalize email
    normalized_email = data.email.lower().strip()

    user_doc = {
        "name": data.name,
        "email": normalized_email,
        "password_hash": hash_password(data.password),
        "target_role": None,
        "skills": [],
        "experience_level": None,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    try:
        result = users_collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        return user_doc
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists"
        )


def authenticate_user(data: LoginRequest) -> str:
    """Verify credentials and return JWT access token."""
    
    normalized_email = data.email.lower().strip()
    user = users_collection.find_one({"email": normalized_email})
    
    # Generic 401 error to prevent email enumeration
    unauth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user:
        raise unauth_exception
        
    if not verify_password(data.password, user["password_hash"]):
        raise unauth_exception
        
    return create_access_token(user_id=str(user["_id"]))


def get_user_by_id(user_id: str) -> dict:
    """Retrieve user by their ObjectId string."""
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        return None
        
    return users_collection.find_one({"_id": obj_id})
