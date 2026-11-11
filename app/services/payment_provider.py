from dataclasses import dataclass


@dataclass
class CheckoutResult:
    authorization_url: str
    reference: str


class PaymentProvider:

    async def initialize_payment(
        self,
        *,
        email: str,
        amount: int,
        currency: str,
        reference: str,
        callback_url: str,
    ) -> CheckoutResult:
        raise NotImplementedError

    async def verify_payment(
        self,
        reference: str,
    ) -> dict:
        raise NotImplementedError
