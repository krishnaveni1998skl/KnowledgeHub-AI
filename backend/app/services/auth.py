"""
Authentication & Authorization Service:
- Password hashing & verification using bcrypt
- Token generation & SHA-256 session management
- Password strength validation
- Password reset token lifecycle
- Initial administrator initialization
"""
import re
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import bcrypt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.schema import User, UserSession, PasswordResetToken

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt (12 rounds)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against the stored bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.warning(f"Password verification encountered error: {e}")
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Enforces strong password policy:
    - At least 8 characters long
    - Contains at least one letter
    - Contains at least one number or special symbol
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[\d\W_]", password):
        return False, "Password must contain at least one number or special character."
    return True, ""


def hash_token(token: str) -> str:
    """Computes SHA-256 hash of a bearer or reset token for secure DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token(length_bytes: int = 32) -> str:
    """Generates a cryptographically strong URL-safe random string."""
    return secrets.token_urlsafe(length_bytes)


def create_user_session(db: Session, user_id: int, hours_valid: Optional[int] = None) -> str:
    """
    Creates a new authenticated session in SQLite.
    Returns the raw bearer token while storing only its SHA-256 hash.
    """
    raw_token = generate_secure_token(32)
    t_hash = hash_token(raw_token)
    duration = hours_valid or settings.SESSION_EXPIRE_HOURS
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=duration)

    session = UserSession(
        user_id=user_id,
        token_hash=t_hash,
        expires_at=expires
    )
    db.add(session)
    db.commit()
    return raw_token


def get_user_from_token(db: Session, token: str) -> Optional[User]:
    """
    Validates a bearer token:
    1. Computes hash
    2. Checks token exists in user_sessions
    3. Checks token has not expired
    4. Checks user is active
    """
    if not token or not token.strip():
        return None

    t_hash = hash_token(token.strip())
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    session = db.query(UserSession).filter(
        UserSession.token_hash == t_hash,
        UserSession.expires_at > now
    ).first()

    if session and session.user and session.user.is_active:
        return session.user
    return None


def invalidate_user_session(db: Session, token: str) -> bool:
    """Revokes a session by deleting the token record."""
    if not token:
        return False
    t_hash = hash_token(token.strip())
    deleted = db.query(UserSession).filter(UserSession.token_hash == t_hash).delete()
    db.commit()
    return deleted > 0


def create_password_reset_token(db: Session, user: User, minutes_valid: Optional[int] = None) -> str:
    """
    Generates a one-time password reset token for the specified user.
    Invalidates any previous unused tokens for that user.
    """
    # Invalidate previous unused reset tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False)
    ).update({"used": True})

    raw_token = generate_secure_token(32)
    t_hash = hash_token(raw_token)
    duration = minutes_valid or settings.PASSWORD_RESET_EXPIRE_MINUTES
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=duration)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=expires,
        used=False
    )
    db.add(reset_record)
    db.commit()
    return raw_token


def verify_and_use_reset_token(db: Session, raw_token: str, new_password: str) -> Tuple[bool, str]:
    """
    Validates and executes a password reset:
    1. Verifies token is valid, unused, and unexpired.
    2. Validates new password strength.
    3. Hashes new password and updates user record.
    4. Marks token as used.
    5. Terminates all active sessions for that user for security.
    """
    if not raw_token or not raw_token.strip():
        return False, "Reset token is required."

    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        return False, msg

    t_hash = hash_token(raw_token.strip())
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    reset_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == t_hash
    ).first()

    if not reset_record:
        return False, "Invalid or expired password reset token."

    if reset_record.used:
        return False, "This password reset token has already been used."

    if reset_record.expires_at < now:
        return False, "This password reset token has expired. Please request a new one."

    user = db.query(User).filter(User.id == reset_record.user_id).first()
    if not user:
        return False, "Associated user account was not found."

    # Update password
    user.hashed_password = hash_password(new_password)
    reset_record.used = True

    # Invalidate all active sessions for this user so old sessions cannot be hijacked
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()

    db.commit()
    logger.info(f"Password successfully reset for user id={user.id}, email={user.email}")
    return True, "Password has been successfully updated. Please log in with your new password."


def ensure_initial_admin(db: Session) -> Optional[dict]:
    """
    Ensures at least one administrator account exists without hardcoding a public password.
    If an admin already exists, does nothing.
    If not, creates an admin using INITIAL_ADMIN_PASSWORD from .env, or generates a secure random password.
    """
    admin_exists = db.query(User).filter(User.role == "admin").first()
    if admin_exists:
        return None

    email = settings.INITIAL_ADMIN_EMAIL.strip().lower()
    full_name = settings.INITIAL_ADMIN_NAME

    # Check if a user with this email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        existing_user.role = "admin"
        db.commit()
        logger.info(f"Existing user '{email}' elevated to administrator.")
        return {"email": email, "elevated": True}

    configured_password = (settings.INITIAL_ADMIN_PASSWORD or "").strip()
    generated = False
    if configured_password:
        plain_password = configured_password
    else:
        plain_password = generate_secure_token(12)
        generated = True

    hashed = hash_password(plain_password)
    admin_user = User(
        email=email,
        full_name=full_name,
        hashed_password=hashed,
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()

    if generated:
        logger.info(
            f"[Security Notice] Initial administrator created: email='{email}'. "
            f"Temporary Password: '{plain_password}'. "
            "Please record or change this password immediately."
        )
    else:
        logger.info(f"[Security Notice] Initial administrator created: email='{email}' from configuration.")

    return {
        "email": email,
        "temporary_password": plain_password if generated else "[CONFIGURED_IN_ENV]",
        "generated": generated
    }
