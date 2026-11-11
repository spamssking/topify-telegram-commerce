from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.payment import Payment
from app.models.plan import Plan
from app.services.payment_service import PaymentService
from app.services.paystack_service import PaystackService


router = APIRouter(
    prefix="/api/paystack",
    tags=["Paystack"],
)


@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str | None = Header(default=None),
):
    """
    Receive and process Paystack webhook events.

    Paystack signs the raw request body using HMAC SHA512.
    The signature is verified before the event is processed.
    """

    # ---------------------------------------------------------
    # Read raw request body
    # ---------------------------------------------------------

    payload = await request.body()

    # ---------------------------------------------------------
    # Verify Paystack signature
    # ---------------------------------------------------------

    if not PaystackService.verify_webhook_signature(
        payload,
        x_paystack_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Paystack signature.",
        )

    # ---------------------------------------------------------
    # Parse JSON after signature verification
    # ---------------------------------------------------------

    try:
        event = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    event_name = event.get("event")
    data = event.get("data") or {}

    print("PAYSTACK WEBHOOK:", event_name)
    print(
        "PAYSTACK REFERENCE:",
        data.get("reference"),
    )

    # ---------------------------------------------------------
    # Only process successful charges
    # ---------------------------------------------------------

    if event_name != "charge.success":
        return {
            "status": True,
            "message": "Event received.",
        }

    reference = data.get("reference")

    if not reference:
        return {
            "status": True,
            "message": "Successful event has no reference.",
        }

    # ---------------------------------------------------------
    # Open database session
    # ---------------------------------------------------------

    db: Session = SessionLocal()

    try:

        # -----------------------------------------------------
        # Find local payment
        # -----------------------------------------------------

        payment = (
            db.query(Payment)
            .filter(
                Payment.provider_reference == reference
            )
            .first()
        )

        if not payment:
            print(
                "PAYSTACK PAYMENT NOT FOUND:",
                reference,
            )

            return {
                "status": True,
                "message": "Payment not found locally.",
            }

        # -----------------------------------------------------
        # Idempotency
        #
        # If Paystack sends the webhook again after we already
        # processed it, do not create another subscription.
        # -----------------------------------------------------

        if payment.status == "PAID":
            return {
                "status": True,
                "message": "Payment already processed.",
            }

        # -----------------------------------------------------
        # Verify transaction directly with Paystack
        # -----------------------------------------------------

        paystack = PaystackService()

        transaction = (
            await paystack.verify_transaction(
                reference
            )
        )

        # -----------------------------------------------------
        # Verify transaction status
        # -----------------------------------------------------

        if transaction.get("status") != "success":
            payment.status = "FAILED"

            db.commit()

            return {
                "status": True,
                "message": "Payment was not successful.",
            }

        # -----------------------------------------------------
        # Verify reference
        # -----------------------------------------------------

        if transaction.get("reference") != reference:
            raise HTTPException(
                status_code=400,
                detail="Paystack reference mismatch.",
            )

        # -----------------------------------------------------
        # Verify amount
        #
        # Paystack amount is in the smallest currency unit.
        # -----------------------------------------------------

        transaction_amount = transaction.get(
            "amount"
        )

        if transaction_amount != payment.amount:
            raise HTTPException(
                status_code=400,
                detail="Paystack amount mismatch.",
            )

        # -----------------------------------------------------
        # Verify currency
        # -----------------------------------------------------

        transaction_currency = transaction.get(
            "currency"
        )

        if transaction_currency != payment.currency:
            raise HTTPException(
                status_code=400,
                detail="Paystack currency mismatch.",
            )

        # -----------------------------------------------------
        # Save Paystack payment information
        # -----------------------------------------------------

        payment.provider_payment_id = str(
            transaction.get("id")
        )

        payment.provider_customer_id = (
            transaction.get("customer", {}).get("id")
        )

        authorization = (
            transaction.get("authorization") or {}
        )

        payment.provider_authorization_code = (
            authorization.get("authorization_code")
        )

        payment.provider_authorization_signature = (
            authorization.get("signature")
        )

        payment.card_brand = (
            authorization.get("brand")
        )

        payment.card_last4 = (
            authorization.get("last4")
        )

        payment.provider_customer_email = (
            transaction.get("customer", {}).get("email")
            or payment.provider_customer_email
        )

        payment.paid_at = datetime.now(
            timezone.utc
        )

        # -----------------------------------------------------
        # Activate subscription
        # -----------------------------------------------------

        plan = (
            db.query(Plan)
            .filter(
                Plan.id == payment.plan_id
            )
            .first()
        )

        if not plan:
            raise HTTPException(
                status_code=404,
                detail="Payment plan not found.",
            )

        payment_service = PaymentService(db)

        if payment.payment_type == "RENEWAL":

            subscription = (
                payment_service.process_renewal_payment(
                    payment=payment,
                    plan=plan,
                )
            )

        else:

            subscription = (
                payment_service.activate_subscription(
                    payment=payment,
                    plan=plan,
                )
            )
        subscription.provider_customer_id = (
            payment.provider_customer_id
        )

        subscription.provider_authorization_code = (
            payment.provider_authorization_code
        )

        subscription.billing_status = "IDLE"
        subscription.billing_attempts = 0
        subscription.billing_last_error = None
        subscription.billing_locked_at = None

        print(
            "SUBSCRIPTION ACTIVATED:",
            subscription.id,
        )

        return {
            "status": True,
            "message": "Payment processed successfully.",
            "payment_id": payment.id,
            "subscription_id": subscription.id,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        print(
            "PAYSTACK WEBHOOK ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process payment webhook.",
        )

    finally:
        db.close()