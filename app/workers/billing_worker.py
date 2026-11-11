# app/workers/billing_worker.py

import asyncio
import uuid

from datetime import (
    datetime,
    timezone,
    timedelta,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.user import User
from app.models.plan import Plan

from app.services.paystack_service import (
    PaystackService,
    PaystackError,
)

from app.services.billing_service import (
    BillingService,
)


POLL_INTERVAL = 30

MAX_BILLING_ATTEMPTS = 3


class BillingWorker:

    def __init__(self):

        self.paystack = PaystackService()

        self.billing = BillingService()

    # =====================================================
    # DATABASE
    # =====================================================

    def get_db(self) -> Session:

        return SessionLocal()

    # =====================================================
    # STARTUP
    # =====================================================

    def print_startup(self):

        print("=" * 60)

        print(
            "Telegram Cloud Storage Billing Worker"
        )

        print("=" * 60)

        print(
            "Billing worker started."
        )

        print(
            f"Polling interval: "
            f"{POLL_INTERVAL} seconds"
        )

        print(
            f"Maximum billing attempts: "
            f"{MAX_BILLING_ATTEMPTS}"
        )

        print("=" * 60)

    # =====================================================
    # FIND DUE SUBSCRIPTION
    # =====================================================

def find_subscription(
    self,
    db: Session,
):
    now = datetime.now(timezone.utc)

    print(
        f"[BILLING QUEUE] "
        f"Checking subscriptions at {now.isoformat()}"
    )

    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.status == "ACTIVE",
            Subscription.auto_renew.is_(True),
        )
        .order_by(
            Subscription.next_billing_at
        )
        .all()
    )

    if not subscriptions:
        print(
            "[BILLING QUEUE] "
            "No ACTIVE auto-renew subscriptions found."
        )
        return None

    for subscription in subscriptions:

        print(
            "[BILLING CHECK] "
            f"id={subscription.id}"
        )

        print(
            "[BILLING CHECK] "
            f"next_billing_at="
            f"{subscription.next_billing_at}"
        )

        print(
            "[BILLING CHECK] "
            f"billing_status="
            f"{subscription.billing_status}"
        )

        print(
            "[BILLING CHECK] "
            f"billing_attempts="
            f"{subscription.billing_attempts}"
        )

        print(
            "[BILLING CHECK] "
            f"billing_locked_at="
            f"{subscription.billing_locked_at}"
        )

        if subscription.next_billing_at is None:
            print(
                "[BILLING CHECK] "
                "SKIP: next_billing_at is NULL"
            )
            continue

        if subscription.next_billing_at > now:
            remaining = (
                subscription.next_billing_at - now
            )

            print(
                "[BILLING CHECK] "
                f"SKIP: not due yet "
                f"(due in {remaining})"
            )
            continue

        if subscription.billing_status != "IDLE":
            print(
                "[BILLING CHECK] "
                f"SKIP: billing_status="
                f"{subscription.billing_status}"
            )
            continue

        if (
            subscription.billing_locked_at
            and subscription.billing_locked_at
            >= now - timedelta(minutes=10)
        ):
            print(
                "[BILLING CHECK] "
                "SKIP: billing lock is active"
            )
            continue

        print(
            "[BILLING QUEUE] "
            "DUE SUBSCRIPTION FOUND"
        )

        print(
            "[BILLING QUEUE] "
            f"id={subscription.id}"
        )

        print(
            "[BILLING QUEUE] "
            f"next_billing_at="
            f"{subscription.next_billing_at}"
        )

        print(
            "[BILLING QUEUE] "
            f"billing_attempts="
            f"{subscription.billing_attempts}"
        )

        return subscription

    print(
        "[BILLING QUEUE] "
        "No subscriptions currently due for billing."
    )

    return None


    # =====================================================
    # ACQUIRE BILLING LOCK
    # =====================================================

    def acquire_billing_lock(
        self,
        db: Session,
        subscription_id: str,
    ):

        print(
            "[BILLING LOCK] "
            "Attempting to acquire billing lock..."
        )

        subscription = (
            db.execute(
                select(Subscription)
                .where(
                    Subscription.id
                    == subscription_id
                )
                .with_for_update(
                    skip_locked=True
                )
            )
            .scalar_one_or_none()
        )

        if not subscription:

            print(
                "[BILLING LOCK] "
                "Subscription is already locked "
                "by another worker."
            )

            db.rollback()

            return None

        now = datetime.now(timezone.utc)

        subscription.billing_status = (
            "PROCESSING"
        )

        subscription.billing_locked_at = now

        subscription.billing_attempts += 1

        subscription.last_billing_attempt_at = now

        db.commit()

        print(
            "[BILLING LOCK] "
            "Lock acquired"
        )

        print(
            f"[BILLING LOCK] "
            f"subscription_id="
            f"{subscription.id}"
        )

        print(
            "[BILLING LOCK] "
            f"billing_status="
            f"{subscription.billing_status}"
        )

        print(
            "[BILLING LOCK] "
            f"attempt="
            f"{subscription.billing_attempts}"
        )

        return subscription

    # =====================================================
    # PROCESS SUBSCRIPTION
    # =====================================================

    async def process_subscription(
        self,
        db: Session,
        subscription: Subscription,
    ):

        print("-" * 60)

        print(
            "[BILLING JOB START]"
        )

        print(
            f"[BILLING JOB] "
            f"subscription_id="
            f"{subscription.id}"
        )

        try:

            user = db.get(
                User,
                subscription.user_id,
            )

            if not user:

                raise ValueError(
                    "Subscription user does not exist."
                )

            plan = db.get(
                Plan,
                subscription.plan_id,
            )

            if not plan:

                raise ValueError(
                    "Subscription plan does not exist."
                )

            if not subscription.auto_renew:

                print(
                    "[BILLING] "
                    "Auto-renew is disabled."
                )

                await self.mark_not_renewing(
                    db,
                    subscription,
                )

                return

            if (
                not subscription.provider_authorization_code
            ):

                raise ValueError(
                    "Subscription has no "
                    "Paystack authorization code."
                )

            print(
                "[BILLING] User loaded"
            )

            print(
                f"[BILLING] "
                f"user_id={user.id}"
            )

            print(
                f"[BILLING] "
                f"email={user.email}"
            )

            print(
                "[BILLING] Plan loaded"
            )

            print(
                f"[BILLING] "
                f"plan_id={plan.id}"
            )

            print(
                f"[BILLING] "
                f"plan_code={plan.code}"
            )

            print(
                f"[BILLING] "
                f"amount={plan.price}"
            )

            print(
                f"[BILLING] "
                f"currency={plan.currency}"
            )

            # -------------------------------------------------
            # CREATE PAYMENT
            # -------------------------------------------------

            reference = (
                f"REN-{uuid.uuid4().hex}"
            )

            payment = Payment(
                user_id=user.id,
                plan_id=plan.id,
                subscription_id=subscription.id,
                provider="PAYSTACK",
                amount=plan.price,
                currency=plan.currency,
                status="PENDING",
                payment_type="RENEWAL",
                provider_reference=reference,
                provider_customer_email=user.email,
                auto_renew_requested=True,
            )

            db.add(payment)

            db.commit()

            db.refresh(payment)

            print(
                "[PAYMENT] "
                "Renewal payment created"
            )

            print(
                f"[PAYMENT] "
                f"payment_id={payment.id}"
            )

            print(
                f"[PAYMENT] "
                f"reference={reference}"
            )

            # -------------------------------------------------
            # PAYSTACK
            # -------------------------------------------------

            print(
                "[PAYSTACK] "
                "Preparing recurring charge..."
            )

            print(
                f"[PAYSTACK] "
                f"subscription_id="
                f"{subscription.id}"
            )

            print(
                f"[PAYSTACK] "
                f"email={user.email}"
            )

            print(
                f"[PAYSTACK] "
                f"amount={plan.price}"
            )

            print(
                f"[PAYSTACK] "
                f"currency={plan.currency}"
            )

            print(
                f"[PAYSTACK] "
                f"reference={reference}"
            )

            print(
                "[PAYSTACK] "
                "Sending authorization charge..."
            )

            result = (
                await self.paystack
                .charge_authorization(
                    authorization_code=(
                        subscription
                        .provider_authorization_code
                    ),
                    email=user.email,
                    amount=plan.price,
                    reference=reference,
                )
            )

            print(
                "[PAYSTACK] "
                "Charge successful"
            )

            print(
                f"[PAYSTACK] "
                f"reference={reference}"
            )

            print(
                f"[PAYSTACK] "
                f"provider_reference="
                f"{result.get('reference')}"
            )

            # -------------------------------------------------
            # UPDATE PAYMENT
            # -------------------------------------------------

            payment.status = "PAID"

            payment.paid_at = (
                datetime.now(timezone.utc)
            )

            payment.provider_payment_id = (
                str(result.get("id"))
                if result.get("id")
                else None
            )

            payment.provider_reference = (
                result.get("reference")
                or reference
            )

            payment.provider_customer_id = (
                result.get("customer", {})
                .get("customer_code")
            )

            payment.provider_authorization_code = (
                result.get(
                    "authorization",
                    {}
                ).get("authorization_code")
            )

            # -------------------------------------------------
            # CALCULATE NEXT BILLING
            # -------------------------------------------------

            next_billing_at = (
                self.billing
                .calculate_next_billing_at(
                    subscription.next_billing_at
                    or datetime.now(
                        timezone.utc
                    ),
                    plan.billing_interval,
                )
            )

            subscription.next_billing_at = (
                next_billing_at
            )

            subscription.ends_at = (
                next_billing_at
            )

            subscription.billing_status = (
                "IDLE"
            )

            subscription.billing_last_error = (
                None
            )

            subscription.billing_locked_at = (
                None
            )

            subscription.status = "ACTIVE"

            db.commit()

            print(
                "[BILLING SUCCESS] "
                "Subscription renewed"
            )

            print(
                f"[BILLING SUCCESS] "
                f"subscription_id="
                f"{subscription.id}"
            )

            print(
                f"[BILLING SUCCESS] "
                f"payment_id="
                f"{payment.id}"
            )

            print(
                f"[BILLING SUCCESS] "
                f"next_billing_at="
                f"{subscription.next_billing_at}"
            )

            print(
                "[BILLING JOB COMPLETE] "
                f"subscription_id="
                f"{subscription.id}"
            )

        except Exception as exc:

            print(
                "[BILLING ERROR]"
            )

            print(
                f"[BILLING ERROR] "
                f"subscription_id="
                f"{subscription.id}"
            )

            print(
                f"[BILLING ERROR] "
                f"error_type="
                f"{type(exc).__name__}"
            )

            print(
                f"[BILLING ERROR] "
                f"error={exc}"
            )

            await self.handle_failure(
                db,
                subscription,
                str(exc),
            )

        print("-" * 60)

    # =====================================================
    # HANDLE FAILURE
    # =====================================================

    async def handle_failure(
        self,
        db: Session,
        subscription: Subscription,
        error: str,
    ):

        print(
            "[BILLING FAILURE] "
            "Processing billing failure..."
        )

        subscription.billing_status = (
            "FAILED"
        )

        subscription.billing_last_error = (
            error
        )

        subscription.billing_locked_at = (
            None
        )

        db.commit()

        print(
            "[BILLING FAILURE] "
            f"subscription_id="
            f"{subscription.id}"
        )

        print(
            "[BILLING FAILURE] "
            f"attempts="
            f"{subscription.billing_attempts}"
        )

        print(
            "[BILLING FAILURE] "
            f"error={error}"
        )

    # =====================================================
    # NO AUTO RENEW
    # =====================================================

    async def mark_not_renewing(
        self,
        db: Session,
        subscription: Subscription,
    ):

        subscription.billing_status = (
            "IDLE"
        )

        subscription.billing_locked_at = (
            None
        )

        db.commit()

        print(
            "[BILLING] "
            "Subscription does not require "
            "automatic renewal."
        )

    # =====================================================
    # RUN
    # =====================================================

    async def run(self):

        self.print_startup()

        while True:

            db = self.get_db()

            try:

                subscription = (
                    self.find_subscription(
                        db
                    )
                )

                if subscription:

                    locked_subscription = (
                        self.acquire_billing_lock(
                            db,
                            subscription.id,
                        )
                    )

                    if locked_subscription:

                        await self.process_subscription(
                            db,
                            locked_subscription,
                        )

                else:

                    print(
                        "[BILLING QUEUE] "
                        "No subscriptions due "
                        "for billing."
                    )

                    await asyncio.sleep(
                        POLL_INTERVAL
                    )

            except Exception as exc:

                print(
                    "[BILLING WORKER ERROR]"
                )

                print(
                    f"[BILLING WORKER ERROR] "
                    f"type={type(exc).__name__}"
                )

                print(
                    f"[BILLING WORKER ERROR] "
                    f"error={exc}"
                )

                await asyncio.sleep(
                    POLL_INTERVAL
                )

            finally:

                db.close()

    # =====================================================
    # SHUTDOWN
    # =====================================================

    async def shutdown(self):

        print("=" * 60)

        print(
            "Billing worker stopped."
        )

        print(
            "Billing worker shutdown complete."
        )

        print("=" * 60)


if __name__ == "__main__":

    worker = BillingWorker()

    try:

        asyncio.run(
            worker.run()
        )

    except KeyboardInterrupt:

        print()

        print(
            "Billing worker interrupted."
        )

        print(
            "Billing worker stopped."
        )
