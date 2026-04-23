"""
Authentication API routes.
Handles user registration, login, profile management, email verification,
password reset, refresh tokens, staff invitation, and account lockout.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re

from app.db.session import get_db
from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_refresh_token, get_current_user, require_admin,
    validate_password_strength, generate_verification_code, generate_secure_token,
    log_audit,
)
from app.core.encryption import encrypt_value
from app.models.user import User, UserRole
from app.models.business import Business
from app.models.audit import AuditLog, StaffInvitation
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse, UserUpdate
from app.schemas.common import (
    SuccessResponse, PasswordResetRequest, PasswordResetConfirm,
    ChangePasswordRequest, StaffInviteRequest, StaffInviteAccept,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


def _build_token_response(user, business, db):
    """Build standardized token response with access + refresh tokens."""
    token_data = {
        "sub": str(user.id),
        "business_id": str(business.id) if business else None,
        "role": user.role.value,
        "email": user.email,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "business_id": str(business.id) if business else None,
            "business_name": business.name if business else "",
            "meta_app_id": settings.META_APP_ID,
            "is_verified": user.is_verified,
            "subscription_plan": business.subscription_plan if business else "free",
        }
    )


@router.post("/register", response_model=TokenResponse)
def register(data: UserRegister, request: Request, db: Session = Depends(get_db)):
    """
    Register a new user and create their business.
    Includes password strength validation and optional email verification.
    """
    # Validate password strength
    password_check = validate_password_strength(data.password)
    if not password_check["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Weak password", "errors": password_check["errors"]}
        )

    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create the business
    slug = _slugify(data.business_name)
    existing_slug = db.query(Business).filter(Business.slug == slug).first()
    if existing_slug:
        slug = f"{slug}-{datetime.utcnow().strftime('%H%M%S')}"
    
    # Encrypt sensitive WhatsApp tokens if provided
    encrypted_wa_token = ""
    if hasattr(data, 'whatsapp_api_token') and data.whatsapp_api_token:
        try:
            encrypted_wa_token = encrypt_value(data.whatsapp_api_token)
        except Exception:
            encrypted_wa_token = data.whatsapp_api_token

    business = Business(
        name=data.business_name,
        slug=slug,
        business_type=data.business_type,
        email=data.email,
        whatsapp_phone_number_id=data.whatsapp_phone_number_id if hasattr(data, 'whatsapp_phone_number_id') else None,
        whatsapp_api_token=encrypted_wa_token,
        whatsapp_verify_token=f"verify_{slug}_{datetime.utcnow().strftime('%Y%m%d')}"
    )
    db.add(business)
    db.flush()
    
    # Generate verification code
    verification_code = generate_verification_code()
    
    # Create the user (admin role for first user)
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.ADMIN,
        business_id=business.id,
        is_active=True,
        is_verified=not settings.REQUIRE_EMAIL_VERIFICATION,
        verification_code=verification_code,
        verification_code_expires=datetime.utcnow() + timedelta(minutes=30),
    )
    db.add(user)
    
    # Audit log
    log_audit(
        db, action="user.register",
        user_email=data.email, business_id=business.id,
        description=f"New business registered: {data.business_name}",
        ip_address=request.client.host if request.client else None,
    )
    
    db.commit()
    db.refresh(user)
    
    # Send welcome + verification emails
    try:
        from app.core.email import email_service
        email_service.send_welcome(data.email, data.full_name, data.business_name)
        if settings.REQUIRE_EMAIL_VERIFICATION:
            email_service.send_verification_code(data.email, verification_code, data.full_name)
    except Exception:
        pass  # Don't fail registration if email fails
    
    return _build_token_response(user, business, db)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    Includes account lockout after too many failed attempts.
    """
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check account lockout
    if user.is_locked:
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to too many failed login attempts. Try again in {remaining + 1} minutes."
        )

    # Verify password
    if not verify_password(data.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked after {settings.MAX_LOGIN_ATTEMPTS} failed attempts. Try again in {settings.LOCKOUT_DURATION_MINUTES} minutes."
            )
        
        remaining_attempts = settings.MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid email or password. {remaining_attempts} attempts remaining."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    
    # Audit log
    log_audit(
        db, action="user.login",
        user_id=user.id, user_email=user.email,
        business_id=user.business_id,
        description="User logged in",
        ip_address=request.client.host if request.client else None,
    )
    
    db.commit()
    
    business = db.query(Business).filter(Business.id == user.business_id).first()
    
    return _build_token_response(user, business, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    payload = decode_refresh_token(refresh_token)
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    business = db.query(Business).filter(Business.id == user.business_id).first()
    
    return _build_token_response(user, business, db)


@router.post("/verify-email")
def verify_email(code: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verify email with 6-digit code."""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified:
        return {"message": "Email already verified"}
    
    if user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    if user.verification_code_expires and user.verification_code_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code expired. Request a new one.")
    
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    db.commit()
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
def resend_verification(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Resend email verification code."""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified:
        return {"message": "Email already verified"}
    
    new_code = generate_verification_code()
    user.verification_code = new_code
    user.verification_code_expires = datetime.utcnow() + timedelta(minutes=30)
    db.commit()
    
    try:
        from app.core.email import email_service
        email_service.send_verification_code(user.email, new_code, user.full_name)
    except Exception:
        pass
    
    return {"message": "Verification code sent"}


@router.post("/forgot-password")
def forgot_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """Send password reset link."""
    user = db.query(User).filter(User.email == data.email).first()
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If the email exists, a reset link has been sent."}
    
    reset_token = generate_secure_token()
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    try:
        from app.core.email import email_service
        email_service.send_password_reset(user.email, reset_token, user.full_name)
    except Exception:
        pass
    
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password using token."""
    user = db.query(User).filter(User.reset_token == data.token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Validate new password
    password_check = validate_password_strength(data.new_password)
    if not password_check["valid"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Weak password", "errors": password_check["errors"]}
        )
    
    user.password_hash = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password (authenticated users)."""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    password_check = validate_password_strength(data.new_password)
    if not password_check["valid"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Weak password", "errors": password_check["errors"]}
        )
    
    user.password_hash = hash_password(data.new_password)
    
    log_audit(
        db, action="user.password_changed",
        user_id=str(user.id), user_email=user.email,
        business_id=str(user.business_id),
        description="Password changed",
    )
    
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the currently authenticated user's profile."""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/me", response_model=UserResponse)
def update_profile(
    data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the currently authenticated user's profile."""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    
    db.commit()
    db.refresh(user)
    return user


# ─── Staff Invitation ────────────────────────────────────────────────

@router.post("/invite-staff")
def invite_staff(
    data: StaffInviteRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Invite a staff member to join the business (admin only)."""
    # Check if already invited or registered
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="This email is already registered")
    
    existing_invite = db.query(StaffInvitation).filter(
        StaffInvitation.email == data.email,
        StaffInvitation.business_id == current_user["business_id"],
        StaffInvitation.is_accepted == "pending",
    ).first()
    if existing_invite:
        raise HTTPException(status_code=400, detail="An invitation is already pending for this email")

    # Check plan limits
    from app.services.subscription_service import subscription_service
    limit_check = subscription_service.check_limit(db, current_user["business_id"], "users")
    if not limit_check.get("allowed", True):
        raise HTTPException(status_code=403, detail=limit_check.get("upgrade_message", "User limit reached"))

    token = generate_secure_token()
    
    invitation = StaffInvitation(
        business_id=current_user["business_id"],
        email=data.email,
        role=data.role,
        invited_by=current_user["user_id"],
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    
    # Get inviter info
    inviter = db.query(User).filter(User.id == current_user["user_id"]).first()
    business = db.query(Business).filter(Business.id == current_user["business_id"]).first()
    
    log_audit(
        db, action="staff.invited",
        user_id=current_user["user_id"], user_email=current_user["email"],
        business_id=current_user["business_id"],
        description=f"Invited {data.email} as {data.role}",
        ip_address=request.client.host if request.client else None,
    )
    
    db.commit()
    
    # Send invitation email
    try:
        from app.core.email import email_service
        email_service.send_staff_invitation(
            data.email,
            inviter.full_name if inviter else "Admin",
            business.name if business else "Business",
            token
        )
    except Exception:
        pass
    
    return {"message": f"Invitation sent to {data.email}", "token": token}


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(data: StaffInviteAccept, db: Session = Depends(get_db)):
    """Accept a staff invitation and create account."""
    invitation = db.query(StaffInvitation).filter(
        StaffInvitation.token == data.token,
        StaffInvitation.is_accepted == "pending",
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    
    if invitation.expires_at < datetime.utcnow():
        invitation.is_accepted = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")
    
    # Validate password
    password_check = validate_password_strength(data.password)
    if not password_check["valid"]:
        raise HTTPException(status_code=400, detail={"message": "Weak password", "errors": password_check["errors"]})
    
    # Create user
    user = User(
        email=invitation.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole(invitation.role),
        business_id=invitation.business_id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    
    invitation.is_accepted = "accepted"
    invitation.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    business = db.query(Business).filter(Business.id == invitation.business_id).first()
    
    return _build_token_response(user, business, db)


# ─── Subscription Info ────────────────────────────────────────────────

@router.get("/subscription")
def get_subscription(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current subscription plan and usage."""
    from app.services.subscription_service import subscription_service
    return subscription_service.get_subscription_info(db, current_user["business_id"])
