import hashlib
import hmac
import json

import httpx

from app.core.config import settings


class PaystackError(Exception):
    pass


class PaystackService:

    def __init__(self):

        self.base_url = (
            settings.paystack_base_url.rstrip("/")
        )

        self.headers = {
            "Authorization": (
                f"Bearer {settings.paystack_secret_key}"
            ),
            "Content-Type": "application/json",
        }

    async def initialize_transaction(
        self,
        *,
        email: str,
        amount: int,
        reference: str,
        callback_url: str | None = None,
        metadata: dict | None = None,
    ) -> dict:

        payload = {
            "email": email,
            "amount": str(amount),
            "currency": "NGN",
            "reference": reference,
        }

        if callback_url:
            payload["callback_url"] = callback_url

        if metadata:
            payload["metadata"] = json.dumps(
                metadata
            )

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                f"{self.base_url}/transaction/initialize",
                headers=self.headers,
                json=payload,
            )

        try:
            data = response.json()
        except Exception:
            raise PaystackError(
                "Invalid response from Paystack."
            )

        if (
            response.status_code >= 400
            or not data.get("status")
        ):

            raise PaystackError(
                data.get(
                    "message",
                    "Unable to initialize Paystack transaction.",
                )
            )

        return data["data"]

    async def verify_transaction(
        self,
        reference: str,
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self.headers,
            )

        try:
            data = response.json()
        except Exception:
            raise PaystackError(
                "Invalid response from Paystack."
            )

        if (
            response.status_code >= 400
            or not data.get("status")
        ):

            raise PaystackError(
                data.get(
                    "message",
                    "Unable to verify Paystack transaction.",
                )
            )

        return data["data"]

    async def charge_authorization(
        self,
        *,
        authorization_code: str,
        email: str,
        amount: int,
        reference: str,
        currency: str = "NGN",
        metadata: dict | None = None,
    ) -> dict:

        payload = {
            "authorization_code": authorization_code,
            "email": email,
            "amount": str(amount),
            "currency": currency,
            "reference": reference,
            "queue": True,
        }

        if metadata:

            payload["metadata"] = json.dumps(
                metadata
            )

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                f"{self.base_url}/transaction/charge_authorization",
                headers=self.headers,
                json=payload,
            )

        try:

            data = response.json()

        except Exception:

            raise PaystackError(
                "Invalid response from Paystack."
            )

        if (
            response.status_code >= 400
            or not data.get("status")
        ):

            raise PaystackError(
                data.get(
                    "message",
                    "Unable to charge authorization.",
                )
            )

        return data["data"]


    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str | None,
    ) -> bool:

        if not signature:
            return False

        expected = hmac.new(
            settings.paystack_secret_key.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(
            expected,
            signature,
        )
