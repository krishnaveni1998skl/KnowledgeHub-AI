"""
Authentication & Authorization API Router:
- Registration (self-registration restricted to viewer role)
- Login (with bcrypt password verification & session tokens)
- Current user profile (/me)
- Logout (token revocation)
- Forgot password & Reset password (with secure dev-mode token helper)
- FastAPI dependencies: get_current_user, require_roles
"""
import re
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field, field_validator, ConfigDict
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.schema import User
from app.services.auth import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_user_session,
    get_user_from_token,
    invalidate_user_session,
    create_password_reset_token,
    verify_and_use_reset_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Access Control"])

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ==========================================
# Pydantic Request / Response Models
# ==========================================

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    email: str = Field(..., min_length=5, max_length=255, description="Valid corporate email address")
    password: str = Field(..., min_length=8, description="Password meeting security policy")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_PATTERN.match(clean):
            raise ValueError("Invalid email format.")
        return clean


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User's registered email")
    password: str = Field(..., min_length=1, description="Account password")
    remember: bool = Field(default=False, description="Persist session for extended duration")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_PATTERN.match(clean):
            raise ValueError("Invalid email format.")
        return clean


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="Email address associated with account")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_PATTERN.match(clean):
            raise ValueError("Invalid email format.")
        return clean


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password meeting security requirements")


class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    token: str
    user: UserProfileResponse
    message: str = "Authentication successful"


# ==========================================
# FastAPI Security Dependencies
# ==========================================

def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Safely extracts token from Authorization: Bearer <token> header."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user_optional(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Returns the authenticated User if a valid Bearer token is provided, or None."""
    token = extract_bearer_token(authorization)
    if not token:
        return None
    return get_user_from_token(db, token)


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
) -> User:
    """Enforces authentication: returns valid User or raises HTTP 401."""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please provide Authorization: Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or token is invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(allowed_roles: List[str]):
    """
    Factory creating a dependency that checks if the authenticated user has one of allowed_roles.
    Raises 403 Forbidden if user lacks necessary privileges.
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)} (current role: {user.role})."
            )
        return user
    return role_checker


# ==========================================
# Authentication Endpoints
# ==========================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new user account.
    Security policy:
    - Never allows client to grant itself an administrator role.
    - New accounts are always assigned default 'viewer' role.
    - Enforces strong password rules and unique email addresses.
    """
    clean_email = request.email.strip().lower()
    clean_name = request.full_name.strip()

    # 1. Check for duplicate email
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in instead."
        )

    # 2. Validate password strength
    is_valid, msg = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    # 3. Create user with safe default role 'viewer'
    hashed = hash_password(request.password)
    new_user = User(
        email=clean_email,
        full_name=clean_name,
        hashed_password=hashed,
        role="viewer",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 4. Create initial authenticated session
    token = create_user_session(db, new_user.id, hours_valid=settings.SESSION_EXPIRE_HOURS)

    logger.info(f"User registered successfully: id={new_user.id}, email={new_user.email}, role={new_user.role}")

    return AuthResponse(
        token=token,
        user=UserProfileResponse.model_validate(new_user),
        message="Registration successful. Welcome to KnowledgeHub AI!"
    )


@router.post("/login", response_model=AuthResponse)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user via email and password.
    Returns a secure session bearer token.
    """
    clean_email = request.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your organization administrator."
        )

    # Calculate session duration: 7 days if remember me is requested, otherwise standard 24 hours
    hours = 7 * 24 if request.remember else settings.SESSION_EXPIRE_HOURS
    token = create_user_session(db, user.id, hours_valid=hours)

    logger.info(f"User logged in: id={user.id}, email={user.email}, role={user.role}")

    return AuthResponse(
        token=token,
        user=UserProfileResponse.model_validate(user),
        message="Sign in successful."
    )


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return UserProfileResponse.model_validate(user)


@router.post("/logout")
def logout_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Revokes the current bearer session token."""
    token = extract_bearer_token(authorization)
    if token:
        invalidate_user_session(db, token)
    return {"message": "You have been successfully logged out."}


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Initiates password recovery.
    Security policy:
    - Does NOT reveal whether the email exists in the system (prevents account enumeration).
    - In development mode (API_ENV='development'), provides dev_reset_token and dev_reset_link
      in the response to allow seamless local verification without an SMTP server.
    - In production, reset instructions would be delivered via encrypted out-of-band email.
    """
    clean_email = request.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email, User.is_active.is_(True)).first()

    raw_token = None
    if user:
        raw_token = create_password_reset_token(db, user, minutes_valid=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        logger.info(f"Password reset initiated for user id={user.id}, email={user.email}")

    response_payload = {
        "message": "If an account exists for this email address, password recovery instructions have been prepared."
    }

    # Development convenience: expose reset token directly in response for local testing
    if settings.API_ENV == "development" and raw_token:
        response_payload["dev_reset_token"] = raw_token
        response_payload["dev_reset_link"] = f"/reset-password?token={raw_token}"
        response_payload["note"] = "Local development mode: reset token provided directly for testing."

    return response_payload


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Validates password reset token and updates the user's password.
    Rejects expired or previously used tokens.
    """
    success, message = verify_and_use_reset_token(db, request.token, request.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return {"message": message}
