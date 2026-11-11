from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CheckoutRequest(BaseModel):

    plan_id: str
    auto_renew: bool = False


class CheckoutResponse(BaseModel):

    payment_id: str

    reference: str

    authorization_url: str

    access_code: str


class PaymentResponse(BaseModel):

    id: str

    amount: int

    currency: str

    status: str

    payment_type: str | None

    provider: str

    provider_payment_id: str | None

    provider_reference: str | None

    card_brand: str | None

    card_last4: str | None

    auto_renew_requested: bool

    paid_at: datetime | None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )

