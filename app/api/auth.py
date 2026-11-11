from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# ---------------------------------------------------------
# REGISTER
# ---------------------------------------------------------

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):

    service = AuthService(db)

    try:

        user, verification_token = service.register(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )

        email_service = EmailService()

        email_service.send_verification_email(
            email=user.email,
            token=verification_token,
        )

        return {
            "message": (
                "Account created successfully. "
                "Please check your email to verify your account."
            )
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()
        print("REGISTRATION ERROR:", repr(exc))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )



# ---------------------------------------------------------
# VERIFY EMAIL
# ---------------------------------------------------------

@router.get(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):

    service = AuthService(db)

    try:

        service.verify_email(token)

        return {
            "message": (
                "Email verified successfully. "
                "Your account is now active."
            )
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------
# RESEND VERIFICATION
# ---------------------------------------------------------

@router.post(
    "/resend-verification",
    response_model=MessageResponse,
)
def resend_verification(
    data: LoginRequest,
    db: Session = Depends(get_db),
):

    email = data.email.lower().strip()

    user = db.execute(
        select(User).where(
            User.email == email
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already verified.",
        )

    service = AuthService(db)

    try:

        verification_token = (
            service.create_new_verification_token(
                user
            )
        )

        email_service = EmailService()

        email_service.send_verification_email(
            email=user.email,
            token=verification_token,
        )

        return {
            "message": (
                "A new verification email has been sent."
            )
        }

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to send verification email.",
        )


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):

    service = AuthService(db)

    try:

        token, user = service.login(
            email=data.email,
            password=data.password,
        )

        return {
            "access_token": token,
            "token_type": "bearer",
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


# ---------------------------------------------------------
# ME
# ---------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
