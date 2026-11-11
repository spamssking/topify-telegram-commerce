from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.subscription import Subscription


class SubscriptionService:

    def __init__(self, db: Session):
        self.db = db

    def get_current(
        self,
        user_id: str,
    ) -> Subscription | None:

        now = datetime.now(timezone.utc)

        return (
            self.db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == "ACTIVE",
                (
                    Subscription.ends_at.is_(None)
                    | (Subscription.ends_at > now)
                ),
            )
            .order_by(
                Subscription.created_at.desc()
            )
            .first()
        )

    def list_user_subscriptions(
        self,
        user_id: str,
    ) -> list[Subscription]:

        return (
            self.db.query(Subscription)
            .filter(
                Subscription.user_id == user_id
            )
            .order_by(
                Subscription.created_at.desc()
            )
            .all()
        )
