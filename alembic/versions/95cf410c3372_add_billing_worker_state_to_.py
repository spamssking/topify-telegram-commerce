"""add billing worker state to subscriptions

Revision ID: 95cf410c3372
Revises: 3cf93cbc39aa
Create Date: 2026-09-29 08:15:02.526269

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '95cf410c3372'
down_revision: Union[str, Sequence[str], None] = '3cf93cbc39aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:

    op.add_column(
        "subscriptions",
        sa.Column(
            "billing_status",
            sa.String(length=30),
            server_default="IDLE",
            nullable=False,
        ),
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "billing_last_error",
            sa.String(length=1000),
            nullable=True,
        ),
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "billing_locked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_subscriptions_billing_status",
        "subscriptions",
        ["billing_status"],
        unique=False,
    )


def downgrade() -> None:

    op.drop_index(
        "ix_subscriptions_billing_status",
        table_name="subscriptions",
    )

    op.drop_column(
        "subscriptions",
        "billing_locked_at",
    )

    op.drop_column(
        "subscriptions",
        "billing_last_error",
    )

    op.drop_column(
        "subscriptions",
        "billing_status",
    )