"""add payment authorization and subscription billing fields

Revision ID: 3cf93cbc39aa
Revises: 157ed82b26fa
Create Date: 2026-09-23 06:28:01.372752
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3cf93cbc39aa"
down_revision: Union[str, Sequence[str], None] = "157ed82b26fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # =========================================================
    # PAYMENTS
    # =========================================================

    op.add_column(
        "payments",
        sa.Column(
            "provider_customer_email",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "payments",
        sa.Column(
            "auto_renew_requested",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_payments_provider_customer_email",
        "payments",
        ["provider_customer_email"],
        unique=False,
    )

    # =========================================================
    # SUBSCRIPTIONS
    # =========================================================

    op.add_column(
        "subscriptions",
        sa.Column(
            "next_billing_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "grace_ends_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "last_billing_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "billing_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_subscriptions_next_billing_at",
        "subscriptions",
        ["next_billing_at"],
        unique=False,
    )

    op.create_index(
        "ix_subscriptions_grace_ends_at",
        "subscriptions",
        ["grace_ends_at"],
        unique=False,
    )


def downgrade() -> None:

    # =========================================================
    # SUBSCRIPTIONS
    # =========================================================

    op.drop_index(
        "ix_subscriptions_grace_ends_at",
        table_name="subscriptions",
    )

    op.drop_index(
        "ix_subscriptions_next_billing_at",
        table_name="subscriptions",
    )

    op.drop_column(
        "subscriptions",
        "billing_attempts",
    )

    op.drop_column(
        "subscriptions",
        "last_billing_attempt_at",
    )

    op.drop_column(
        "subscriptions",
        "grace_ends_at",
    )

    op.drop_column(
        "subscriptions",
        "next_billing_at",
    )

    # =========================================================
    # PAYMENTS
    # =========================================================

    op.drop_index(
        "ix_payments_provider_customer_email",
        table_name="payments",
    )

    op.drop_column(
        "payments",
        "auto_renew_requested",
    )

    op.drop_column(
        "payments",
        "provider_customer_email",
    )
