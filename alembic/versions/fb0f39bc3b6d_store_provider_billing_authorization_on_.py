"""store provider billing authorization on subscriptions

Revision ID: fb0f39bc3b6d
Revises: b44651e1d187
Create Date: 2026-09-29 09:05:55.406519

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'fb0f39bc3b6d'
down_revision: Union[str, Sequence[str], None] = 'b44651e1d187'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "subscriptions",
        sa.Column(
            "provider_customer_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "provider_authorization_code",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_subscriptions_provider_customer_id",
        "subscriptions",
        ["provider_customer_id"],
        unique=False,
    )


def downgrade() -> None:

    op.drop_index(
        "ix_subscriptions_provider_customer_id",
        table_name="subscriptions",
    )

    op.drop_column(
        "subscriptions",
        "provider_authorization_code",
    )

    op.drop_column(
        "subscriptions",
        "provider_customer_id",
    )
