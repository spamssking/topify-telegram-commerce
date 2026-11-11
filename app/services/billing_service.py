# app/services/billing_service.py

from calendar import monthrange
from datetime import datetime


class BillingService:

    # =====================================================
    # ADD ONE MONTH
    # =====================================================

    @staticmethod
    def add_month(
        value: datetime,
    ) -> datetime:

        year = value.year
        month = value.month

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

        day = min(
            value.day,
            monthrange(year, month)[1],
        )

        return value.replace(
            year=year,
            month=month,
            day=day,
        )

    # =====================================================
    # ADD ONE YEAR
    # =====================================================

    @staticmethod
    def add_year(
        value: datetime,
    ) -> datetime:

        year = value.year + 1

        # Handles February 29 correctly.
        day = min(
            value.day,
            monthrange(
                year,
                value.month,
            )[1],
        )

        return value.replace(
            year=year,
            day=day,
        )

    # =====================================================
    # CALCULATE NEXT BILLING DATE
    # =====================================================

    @classmethod
    def calculate_next_billing_at(
        cls,
        starts_at: datetime,
        billing_interval: str | None,
    ) -> datetime | None:

        if not billing_interval:
            return None

        interval = (
            billing_interval
            .strip()
            .upper()
        )

        # Support both naming styles.
        #
        # Existing database:
        #     MONTH
        #
        # Application:
        #     MONTHLY
        #
        if interval in {
            "MONTH",
            "MONTHLY",
        }:

            return cls.add_month(
                starts_at
            )

        if interval in {
            "YEAR",
            "YEARLY",
            "ANNUAL",
            "ANNUALLY",
        }:

            return cls.add_year(
                starts_at
            )

        raise ValueError(
            f"Unsupported billing interval: "
            f"{billing_interval}"
        )
