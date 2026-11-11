"""add payment provider authorization fields

Revision ID: 157ed82b26fa
Revises: 6a26cc25f2ba
Create Date: 2026-09-20 04:04:27.957001

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "157ed82b26fa"
down_revision: Union[str, Sequence[str], None] = "6a26cc25f2ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Paystack provider authorization fields to payments."""

    op.add_column(
        "payments",
        sa.Column(
            "provider_authorization_code",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "payments",
        sa.Column(
            "provider_authorization_signature",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_payments_provider_authorization_code",
        "payments",
        ["provider_authorization_code"],
        unique=False,
    )

    op.create_index(
        "ix_payments_provider_authorization_signature",
        "payments",
        ["provider_authorization_signature"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Paystack provider authorization fields from payments."""

    op.drop_index(
        "ix_payments_provider_authorization_signature",
        table_name="payments",
    )

    op.drop_index(
        "ix_payments_provider_authorization_code",
        table_name="payments",
    )

    op.drop_column(
        "payments",
        "provider_authorization_signature",
    )

    op.drop_column(
        "payments",
        "provider_authorization_code",
    )
