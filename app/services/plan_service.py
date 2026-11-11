from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.user import User


class PlanService:

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def validate_file_size(
        user: User,
        file_size: int,
    ) -> None:
        if not user.plan:
            raise ValueError(
                "User does not have an active plan."
            )

        max_size = user.plan.max_file_size_bytes

        if file_size > max_size:
            max_mb = max_size / 1024 / 1024

            raise ValueError(
                f"File is too large for your "
                f"{user.plan.name} plan. "
                f"Maximum file size is "
                f"{max_mb:.2f} MB."
            )

    def list_active_plans(self) -> list[Plan]:
        return (
            self.db.query(Plan)
            .filter(
                Plan.is_active.is_(True)
            )
            .order_by(
                Plan.sort_order.asc(),
                Plan.price.asc(),
            )
            .all()
        )

    def get_plan(self, plan_id: str) -> Plan | None:
        return (
            self.db.query(Plan)
            .filter(
                Plan.id == plan_id,
                Plan.is_active.is_(True),
            )
            .first()
        )

    def get_plan_by_code(self, code: str) -> Plan | None:
        return (
            self.db.query(Plan)
            .filter(
                Plan.code == code,
                Plan.is_active.is_(True),
            )
            .first()
        )
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.user import User


class PlanService:

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def validate_file_size(
        user: User,
        file_size: int,
    ) -> None:
        if not user.plan:
            raise ValueError(
                "User does not have an active plan."
            )

        max_size = user.plan.max_file_size_bytes

        if file_size > max_size:
            max_mb = max_size / 1024 / 1024

            raise ValueError(
                f"File is too large for your "
                f"{user.plan.name} plan. "
                f"Maximum file size is "
                f"{max_mb:.2f} MB."
            )

    def list_active_plans(self) -> list[Plan]:
        return (
            self.db.query(Plan)
            .filter(
                Plan.is_active.is_(True)
            )
            .order_by(
                Plan.sort_order.asc(),
                Plan.price.asc(),
            )
            .all()
        )

    def get_plan(self, plan_id: str) -> Plan | None:
        return (
            self.db.query(Plan)
            .filter(
                Plan.id == plan_id,
                Plan.is_active.is_(True),
            )
            .first()
        )

    def get_plan_by_code(self, code: str) -> Plan | None:
        return (
            self.db.query(Plan)
            .filter(
                Plan.code == code,
                Plan.is_active.is_(True),
            )
            .first()
        )
