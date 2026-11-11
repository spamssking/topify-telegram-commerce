import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.plan import Plan
from app.models.subscription import Subscription


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


class AuthService:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # PASSWORD
    # ---------------------------------------------------------

    def hash_password(
        self,
        password: str,
    ) -> str:
        return pwd_context.hash(password)

    def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return pwd_context.verify(
            password,
            password_hash,
        )

    # ---------------------------------------------------------
    # VERIFICATION TOKEN
    # ---------------------------------------------------------

    @staticmethod
    def hash_verification_token(
        token: str,
    ) -> str:
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def generate_verification_token() -> str:
        return secrets.token_urlsafe(32)

    # ---------------------------------------------------------
    # JWT
    # ---------------------------------------------------------

    def create_access_token(
        self,
        user_id: str,
    ) -> str:

        now = datetime.now(timezone.utc)

        expires = (
            now
            + timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )
        )

        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": expires,
            "jti": secrets.token_hex(16),
        }

        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    # ---------------------------------------------------------
    # REGISTER
    # ---------------------------------------------------------

    def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> tuple[User, str]:

        email = email.lower().strip()

        # -----------------------------------------------------
        # Check for existing account
        # -----------------------------------------------------

        existing = self.db.execute(
            select(User).where(
                User.email == email
            )
        ).scalar_one_or_none()

        if existing:
            raise ValueError(
                "An account with this email already exists."
            )

        # -----------------------------------------------------
        # Find the default FREE plan
        # -----------------------------------------------------

        free_plan = self.db.execute(
            select(Plan).where(
                Plan.code == "FREE",
                Plan.is_active.is_(True),
                Plan.is_default.is_(True),
            )
        ).scalar_one_or_none()

        if not free_plan:
            raise RuntimeError(
                "Default FREE plan is not configured."
            )

        # -----------------------------------------------------
        # Generate email verification token
        # -----------------------------------------------------

        verification_token = (
            self.generate_verification_token()
        )

        verification_token_hash = (
            self.hash_verification_token(
                verification_token
            )
        )

        verification_expires = (
            datetime.now(timezone.utc)
            + timedelta(hours=24)
        )

        # -----------------------------------------------------
        # Create user
        # -----------------------------------------------------

        user = User(
            email=email,
            password_hash=self.hash_password(password),
            full_name=full_name,

            # The user's quota comes from the Plan.
            plan_id=free_plan.id,

            # User has used nothing yet.
            storage_used=0,

            is_active=True,
            is_verified=False,

            email_verification_token_hash=(
                verification_token_hash
            ),

            email_verification_expires_at=(
                verification_expires
            ),
        )

        self.db.add(user)

        # Flush gives us user.id before committing.
        self.db.flush()

        # -----------------------------------------------------
        # Create initial FREE subscription
        # -----------------------------------------------------

        subscription = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="ACTIVE",
            starts_at=datetime.now(timezone.utc),
            ends_at=None,
            auto_renew=False,
            provider_subscription_id=None,
        )

        self.db.add(subscription)

        # -----------------------------------------------------
        # Commit user + subscription together
        # -----------------------------------------------------

        self.db.commit()

        self.db.refresh(user)

        return user, verification_token

    # ---------------------------------------------------------
    # VERIFY EMAIL
    # ---------------------------------------------------------

    def verify_email(
        self,
        token: str,
    ) -> User:

        token_hash = self.hash_verification_token(
            token
        )

        user = self.db.execute(
            select(User).where(
                User.email_verification_token_hash
                == token_hash
            )
        ).scalar_one_or_none()

        if not user:
            raise ValueError(
                "Invalid verification token."
            )

        if user.is_verified:
            return user

        if (
            user.email_verification_expires_at is None
            or user.email_verification_expires_at
            < datetime.now(timezone.utc)
        ):
            raise ValueError(
                "Verification token has expired."
            )

        user.is_verified = True

        user.verified_at = datetime.now(
            timezone.utc
        )

        # Token can never be used again.
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None

        self.db.commit()
        self.db.refresh(user)

        return user

    # ---------------------------------------------------------
    # RESEND VERIFICATION
    # ---------------------------------------------------------

    def create_new_verification_token(
        self,
        user: User,
    ) -> str:

        if user.is_verified:
            raise ValueError(
                "This email address is already verified."
            )

        verification_token = (
            self.generate_verification_token()
        )

        user.email_verification_token_hash = (
            self.hash_verification_token(
                verification_token
            )
        )

        user.email_verification_expires_at = (
            datetime.now(timezone.utc)
            + timedelta(hours=24)
        )

        self.db.commit()
        self.db.refresh(user)

        return verification_token

    # ---------------------------------------------------------
    # LOGIN
    # ---------------------------------------------------------

    def login(
        self,
        email: str,
        password: str,
    ) -> tuple[str, User]:

        email = email.lower().strip()

        user = self.db.execute(
            select(User).where(
                User.email == email
            )
        ).scalar_one_or_none()

        if not user:
            raise ValueError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise ValueError(
                "Account is disabled."
            )

        if not user.is_verified:
            raise ValueError(
                "Please verify your email before logging in."
            )

        if not self.verify_password(
            password,
            user.password_hash,
        ):
            raise ValueError(
                "Invalid email or password."
            )

        user.last_login_at = datetime.now(
            timezone.utc
        )

        self.db.commit()
        self.db.refresh(user)

        access_token = self.create_access_token(
            user.id
        )

        return access_token, user