from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.plan import PlanResponse


class SubscriptionResponse(BaseModel):
    id: str
    status: str
    starts_at: datetime
    ends_at: datetime | None
    auto_renew: bool

    plan: PlanResponse

    model_config = ConfigDict(
        from_attributes=True,
    )
