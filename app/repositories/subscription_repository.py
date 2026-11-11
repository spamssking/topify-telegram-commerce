from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription


class SubscriptionRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def get_due_subscription(
        self,
    ) -> Subscription | None:

        now = datetime.now(timezone.utc)

        result = self.db.execute(
            select(Subscription)
            .where(
                Subscription.status == "ACTIVE",
                Subscription.auto_renew.is_(True),
                Subscription.next_billing_at.is_not(None),
                Subscription.next_billing_at <= now,
                Subscription.billing_status == "IDLE",
            )
            .order_by(
                Subscription.next_billing_at.asc()
            )
            .with_for_update(
                skip_locked=True
            )
            .limit(1)
        )

        return result.scalar_one_or_none()
