from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.payment import Payment
from app.models.plan import Plan

from app.schemas.payment import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentResponse,
)

from app.services.payment_service import (
    PaymentService,
)

from app.services.plan_service import (
    PlanService,
)


router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
)


# ============================================================
# CREATE CHECKOUT
# ============================================================

@router.post(
    "/checkout",
    response_model=CheckoutResponse,
)
async def create_checkout(
    data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # CHECK USER ACCOUNT
    # --------------------------------------------------------

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address is not verified.",
        )

    # --------------------------------------------------------
    # GET PLAN
    # --------------------------------------------------------

    plan_service = PlanService(db)

    plan = plan_service.get_plan(
        data.plan_id
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found.",
        )

    # --------------------------------------------------------
    # MAKE SURE THIS PLAN REQUIRES PAYMENT
    # --------------------------------------------------------

    if plan.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This plan does not require payment.",
        )

    # --------------------------------------------------------
    # CREATE PAYMENT / INITIALIZE PAYSTACK
    # --------------------------------------------------------

    payment_service = PaymentService(db)

    try:

        payment, checkout_data = (
            await payment_service.create_checkout(
                user=current_user,
                plan=plan,
                 auto_renew=data.auto_renew,
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        print(
            "PAYSTACK CHECKOUT ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to initialize payment.",
        )

    # --------------------------------------------------------
    # RETURN PAYSTACK CHECKOUT INFORMATION
    # --------------------------------------------------------

    return CheckoutResponse(
        payment_id=payment.id,
        reference=payment.provider_reference,
        authorization_url=(
            checkout_data[
                "authorization_url"
            ]
        ),
        access_code=(
            checkout_data[
                "access_code"
            ]
        ),
    )


# ============================================================
# GET ALL PAYMENTS FOR CURRENT USER
# ============================================================

@router.get(
    "",
    response_model=list[PaymentResponse],
)
def get_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    payments = (
        db.query(Payment)
        .filter(
            Payment.user_id == current_user.id
        )
        .order_by(
            Payment.created_at.desc()
        )
        .all()
    )

    return payments

# ============================================================
# GET PAYMENT STATUS
# ============================================================

@router.get(
    "/status/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == current_user.id,
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return payment



# ============================================================
# GET ONE PAYMENT
# ============================================================

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == current_user.id,
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return payment
