"""
app/routes/auth.py

Authentication API routes: Registration, Login, and Me.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from typing_extensions import Annotated

from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services import auth_service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
def register(data: RegisterRequest):
    """
    Register a new user with name, email, and password.
    Returns safe user data without the password hash.
    """
    user_doc = auth_service.register_user(data)
    return UserResponse(**user_doc)


@router.post(
    "/login", 
    response_model=TokenResponse,
    summary="Login and get an access token"
)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Authenticate a user using OAuth2 form data (username and password).
    Returns a JWT access token.
    """
    # OAuth2PasswordRequestForm uses 'username' instead of 'email'
    try:
        login_data = LoginRequest(email=form_data.username, password=form_data.password)
    except Exception:
        # If the user enters a non-email in Swagger, it throws a ValidationError
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = auth_service.authenticate_user(login_data)
    return TokenResponse(access_token=token)


@router.get(
    "/me", 
    response_model=UserResponse,
    summary="Get current user profile"
)
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get the currently authenticated user's profile information.
    Requires a valid JWT Bearer token.
    """
    return UserResponse(**current_user)
