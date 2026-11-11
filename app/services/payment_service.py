# app/services/payment_service.py

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings

from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User

from app.repositories.payment_repository import (
    PaymentRepository,
)

from app.services.billing_service import (
    BillingService,
)

from app.services.paystack_service import (
    PaystackService,
)


class PaymentService:

    def __init__(
        self,
        db: Session,
    ):

        self.db = db

        self.payments = PaymentRepository(
            db
        )

        self.paystack = PaystackService()

    # =====================================================
    # CREATE PENDING PAYMENT
    # =====================================================

    def create_pending_payment(
        self,
        *,
        user: User,
        plan: Plan,
        provider: str,
    ) -> Payment:

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            provider=provider,
            amount=plan.price,
            currency=plan.currency,
            status="PENDING",
            payment_type="SUBSCRIPTION",
            provider_reference=str(
                uuid.uuid4()
            ),
        )

        self.db.add(payment)

        self.db.commit()

        self.db.refresh(payment)

        return payment

    # =====================================================
    # CREATE PAYSTACK CHECKOUT
    # =====================================================

    async def create_checkout(
        self,
        *,
        user: User,
        plan: Plan,
        auto_renew: bool = False,
    ):

        if not user.is_active:

            raise ValueError(
                "Account is disabled."
            )

        if not user.is_verified:

            raise ValueError(
                "Email address is not verified."
            )

        if not plan.is_active:

            raise ValueError(
                "Plan is not available."
            )

        if plan.code == "FREE":

            raise ValueError(
                "The free plan does not require payment."
            )

        if plan.price <= 0:

            raise ValueError(
                "Plan price is invalid."
            )

        # -------------------------------------------------
        # Validate billing interval
        # -------------------------------------------------

        if not plan.billing_interval:

            raise ValueError(
                "Paid plan does not have a billing interval."
            )

        # -------------------------------------------------
        # Generate Paystack reference
        # -------------------------------------------------

        reference = (
            f"SUB-{uuid.uuid4().hex}"
        )

        # -------------------------------------------------
        # Create local payment record
        # -------------------------------------------------

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            provider="PAYSTACK",
            amount=plan.price,
            currency=plan.currency,
            status="PENDING",
            payment_type="SUBSCRIPTION",
            provider_reference=reference,
            provider_customer_email=user.email,
            auto_renew_requested=auto_renew,
        )

        self.db.add(payment)

        self.db.commit()

        self.db.refresh(payment)

        # -------------------------------------------------
        # Paystack callback URL
        # -------------------------------------------------

        callback_url = (
            f"{settings.frontend_url}"
            "/payment/callback"
        )

        # -------------------------------------------------
        # Initialize Paystack transaction
        # -------------------------------------------------

        try:

            checkout = (
                await self.paystack
                .initialize_transaction(
                    email=user.email,
                    amount=plan.price,
                    reference=reference,
                    callback_url=callback_url,
                    metadata={
                        "payment_id": payment.id,
                        "user_id": user.id,
                        "plan_id": plan.id,
                        "auto_renew": auto_renew,
                    },
                )
            )

        except Exception:

            payment.status = "FAILED"

            self.db.commit()

            raise

        return (
            payment,
            checkout,
        )

    # =====================================================
    # ACTIVATE SUBSCRIPTION
    # =====================================================

    def activate_subscription(
        self,
        *,
        payment: Payment,
        plan: Plan,
    ) -> Subscription:

        # -------------------------------------------------
        # Load user
        # -------------------------------------------------

        user = (
            self.db.query(User)
            .filter(
                User.id == payment.user_id
            )
            .first()
        )

        if not user:

            raise ValueError(
                "Payment user not found."
            )

        # -------------------------------------------------
        # Prevent duplicate activation
        # -------------------------------------------------

        if payment.status == "PAID":

            if payment.subscription_id:

                existing = (
                    self.db.query(Subscription)
                    .filter(
                        Subscription.id
                        == payment.subscription_id
                    )
                    .first()
                )

                if existing:

                    return existing

        # -------------------------------------------------
        # Current time
        # -------------------------------------------------

        now = datetime.now(
            timezone.utc
        )

        # -------------------------------------------------
        # Calculate subscription dates
        # -------------------------------------------------

        next_billing_at = (
            BillingService.calculate_next_billing_at(
                starts_at=now,
                billing_interval=(
                    plan.billing_interval
                ),
            )
        )

        # -------------------------------------------------
        # Mark payment as paid
        # -------------------------------------------------

        payment.status = "PAID"

        payment.paid_at = (
            payment.paid_at or now
        )

        # -------------------------------------------------
        # Create subscription
        # -------------------------------------------------

        subscription = Subscription(
            user_id=user.id,

            plan_id=plan.id,

            status="ACTIVE",

            starts_at=now,

            ends_at=next_billing_at,

            next_billing_at=next_billing_at,

            grace_ends_at=None,

            last_billing_attempt_at=None,

            billing_attempts=0,

            auto_renew=(
                payment.auto_renew_requested
            ),

            provider_subscription_id=(
                payment.provider_payment_id
            ),

            provider_customer_id=(
                payment.provider_customer_id
            ),

            provider_authorization_code=(
                payment.provider_authorization_code
            ),

            billing_status="IDLE",

            billing_last_error=None,

            billing_locked_at=None,
        )

        self.db.add(subscription)

        self.db.flush()

        # -------------------------------------------------
        # Connect payment to subscription
        # -------------------------------------------------

        payment.subscription_id = (
            subscription.id
        )

        # -------------------------------------------------
        # Update user's current plan
        # -------------------------------------------------

        user.plan_id = plan.id

        # -------------------------------------------------
        # Commit everything together
        # -------------------------------------------------

        self.db.commit()

        self.db.refresh(
            subscription
        )

        return subscription
