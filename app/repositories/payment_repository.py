from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment


class PaymentRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def create(
        self,
        payment: Payment,
    ) -> Payment:

        self.db.add(payment)

        self.db.commit()

        self.db.refresh(payment)

        return payment

    def get_by_id(
        self,
        payment_id: str,
    ) -> Payment | None:

        return self.db.get(
            Payment,
            payment_id,
        )

    def get_by_reference(
        self,
        reference: str,
    ) -> Payment | None:

        result = self.db.execute(
            select(Payment).where(
                Payment.provider_reference
                == reference
            )
        )

        return result.scalar_one_or_none()

    def get_user_payment(
        self,
        payment_id: str,
        user_id: str,
    ) -> Payment | None:

        result = self.db.execute(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    def list_user_payments(
        self,
        user_id: str,
    ) -> list[Payment]:

        result = self.db.execute(
            select(Payment)
            .where(
                Payment.user_id == user_id
            )
            .order_by(
                Payment.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )
