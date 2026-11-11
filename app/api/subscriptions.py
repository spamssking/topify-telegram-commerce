from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_service import SubscriptionService


router = APIRouter(
    prefix="/api",
    tags=["Subscriptions"],
)


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
)
def get_current_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SubscriptionService(db)

    subscription = service.get_current(
        current_user.id
    )

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="No active subscription.",
        )

    return subscription


@router.get(
    "/subscriptions",
    response_model=list[SubscriptionResponse],
)
def get_subscription_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SubscriptionService(db)

    return service.list_user_subscriptions(
        current_user.id
    )
